import json
import secrets
from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from uk_bin_collection.uk_bin_collection.common import check_uprn, date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# Unchanged from the previous implementation - the same AES-256-CBC key and IV
# are still in use on the new endpoints, in both directions.
key_hex = "F57E76482EE3DC3336495DEDEEF3962671B054FE353E815145E29C5689F72FEC"
iv_hex = "2CBF4FC35C69B82362D393A4F0B9971A"

BASE_URL = "https://itouchvision.app/portal/itouchvision/gdsv5"

# Identifiers for Buckinghamshire's "Check your next bin collection date" form.
# P_CLIENT_ID and P_COUNCIL_ID are the same values the retired kmbd endpoint
# used; the rest identify the form itself on iTouchVision's form engine.
ACCESS_KEY = "FA353FC740600CCE617BE0534D090A8C09AD3DCC"
CLIENT_ID = 152
COUNCIL_ID = 34505
CATEGORY_ID = 18428
FORM_ID = 2299
PAGE_ID = 52742
ADDRESS_ITEM_ID = "666224"
UPRN_ITEM_ID = "666227"

# Sent on the plugin/* calls but not on service/saveqadata, mirroring the
# council's own site. Appears to be a static per-deployment value rather than
# anything minted per session - a fresh session with a randomly generated
# sessionid is accepted alongside it.
BEARER_TOKEN = "SOcNAeuNQh/A6lmc6dd69Q=="

REQUEST_TIMEOUT = 15


class CouncilClass(AbstractGetBinDataClass):
    """
    Buckinghamshire Council, via iTouchVision's form engine.

    The council retired the single-call /kmbd/collectionDay endpoint. That URL
    still resolves and still returns a valid encrypted response, but the payload
    is permanently {"collectionDay": null} - which is why the previous
    implementation failed with an opaque "'NoneType' object is not iterable"
    rather than an error that pointed anywhere useful.

    Collection data now comes from a four-step session against the generic form
    engine at /gdsv5/:

      1. service/saveqadata        - submit the UPRN, receive a report id
      2. plugin/getformdata        - fetch the form definition
      3. plugin/getWSRInputMapping - discover the web service's expected inputs
      4. plugin/getWSRResult       - retrieve the collection table

    Steps 2 and 3 are discovery rather than overhead: step 2 locates the
    WEB_SERVICE_REF item by type (so a form rebuild that renumbers items does
    not break us), and step 3 returns the name and value of every input step 4
    expects (so an added input is picked up rather than silently omitted).
    """

    def encode_body(self, payload: dict) -> str:
        data_bytes = json.dumps(payload).encode("utf-8")

        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data_bytes) + padder.finalize()

        cipher = Cipher(
            algorithms.AES(bytes.fromhex(key_hex)),
            modes.CBC(bytes.fromhex(iv_hex)),
            backend=default_backend(),
        )
        encryptor = cipher.encryptor()
        return (encryptor.update(padded_data) + encryptor.finalize()).hex()

    def decode_response(self, hex_input: str) -> Any:
        stripped = hex_input.strip()
        if not stripped or not all(c in "0123456789ABCDEFabcdef" for c in stripped):
            raise ValueError(f"Expected a hex-encoded response, got: {hex_input[:200]}")

        cipher = Cipher(
            algorithms.AES(bytes.fromhex(key_hex)),
            modes.CBC(bytes.fromhex(iv_hex)),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        decrypted_padded = (
            decryptor.update(bytes.fromhex(stripped)) + decryptor.finalize()
        )

        unpadder = padding.PKCS7(128).unpadder()
        plaintext_bytes = unpadder.update(decrypted_padded) + unpadder.finalize()

        return json.loads(plaintext_bytes.decode("utf-8"))

    def _post_encrypted(self, session, path: str, payload: dict) -> Any:
        response = session.post(
            f"{BASE_URL}/{path}",
            data=self.encode_body(payload),
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return self.decode_response(response.text)

    def _get_plugin(self, session, name: str, payload: dict) -> Any:
        response = session.get(
            f"{BASE_URL}/plugin/{name}",
            headers={
                "authorization": f"Bearer {BEARER_TOKEN}",
                "p_parameter": self.encode_body(payload),
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return self.decode_response(response.text)

    @staticmethod
    def _find_web_service_item(form_data: dict) -> tuple:
        """Locate the form's web-service item by type rather than by id."""
        for page in form_data.get("PAGES", []):
            for region in page.get("REGIONS", []):
                for item in region.get("ITEMS", []):
                    if item.get("I_TYPE") == "WEB_SERVICE_REF":
                        return item.get("I_ID"), item.get("I_WS_ID")
        raise ValueError(
            "No WEB_SERVICE_REF item in the Buckinghamshire form definition - "
            "the council's form has likely been restructured."
        )

    @staticmethod
    def _parse_collection_date(raw_date: str, today: datetime) -> datetime:
        """
        Turn "Saturday 5 September" into a real date.

        The council publishes no year, so it has to be inferred. Parse against
        the current year first; if that lands in the past, the listing has
        crossed a year boundary and the date belongs to next year. Yesterday is
        tolerated so a collection earlier today is not pushed twelve months out.
        """
        parsed = datetime.strptime(raw_date.split(" ", 1)[1].strip(), "%d %B")

        for year in (today.year, today.year + 1):
            try:
                candidate = parsed.replace(year=year)
            except ValueError:
                # 29 February in a non-leap year.
                continue
            if (candidate.date() - today.date()).days >= -1:
                return candidate

        raise ValueError(f"Could not resolve a year for collection date: {raw_date}")

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn") or ""
        check_uprn(user_uprn)

        session = requests.Session()
        session.headers.update(
            {
                "accept": "application/json",
                "content-type": "application/json; charset=UTF-8",
                "origin": "https://connect.buckinghamshire.gov.uk",
                # Client-generated; the server accepts any value here.
                "sessionid": secrets.token_hex(16),
                "user-agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
                ),
            }
        )

        # 1. Submit the UPRN. Only REPORT_UPRN is required - the council's own
        #    site also sends the full address, coordinates and property key, but
        #    the form's hidden field is derived from the UPRN alone, so none of
        #    that personal data needs to leave the user's machine.
        submission = self._post_encrypted(
            session,
            "service/saveqadata",
            {
                "P_ACCESS_KEY": ACCESS_KEY,
                "P_APP_ID": 0,
                "P_REPORT_ID": None,
                "P_USER_ID": None,
                "P_CATEGORY_ID": CATEGORY_ID,
                "P_CLIENT_ID": CLIENT_ID,
                "P_COUNCIL_ID": COUNCIL_ID,
                "P_FORM_ID": FORM_ID,
                "LANG_CODE": "EN",
                "P_ALLOW_START_PAGE": 0,
                "P_SKIPPED_PAGE_ID": "",
                "P_PAGE_ID": PAGE_ID,
                "P_REPORT_DATA": {
                    "REPORT_DATA": [
                        {"ANSWER": {"ID": ""}, "QUESTION": {"VALUE": "honeypot"}},
                        {
                            "ANSWER": {
                                "ID": "",
                                "VALUE": {
                                    "LOCATION_DATA": {"REPORT_UPRN": int(user_uprn)}
                                },
                            },
                            "QUESTION": {
                                "ID": ADDRESS_ITEM_ID,
                                "VALUE": " Your address",
                            },
                        },
                        {
                            "ANSWER": {"ID": "", "VALUE": "UPRN='#REPORT_UPRN#'"},
                            "QUESTION": {
                                "ID": UPRN_ITEM_ID,
                                "VALUE": "-Hidden- Selected UPRN",
                            },
                        },
                    ]
                },
            },
        )

        report_id = submission.get("P_REPORT_ID")
        if not report_id:
            raise ValueError(
                f"Buckinghamshire rejected the UPRN submission: {submission}"
            )

        # 2. Fetch the form definition and locate the web-service item.
        form_data = self._get_plugin(
            session,
            "getformdata",
            {
                "P_CATEGORY_ID": CATEGORY_ID,
                "P_CLIENT_ID": CLIENT_ID,
                "P_ACCESS_KEY": ACCESS_KEY,
                "LANG_CODE": "EN",
                "P_REPORT_ID": report_id,
                "P_USER_ID": None,
            },
        )
        item_id, ws_id = self._find_web_service_item(form_data)

        service_params = {
            "P_CLIENT_ID": CLIENT_ID,
            "P_ACCESS_KEY": ACCESS_KEY,
            "LANG_CODE": "EN",
            "P_ITEM_ID": item_id,
            "P_WS_ID": ws_id,
            "P_REPORT_ID": report_id,
        }

        # 3. Ask the web service what inputs it wants, and build the payload
        #    from its own answer.
        mapping = self._get_plugin(
            session,
            "getWSRInputMapping",
            {**service_params, "P_USER_ID": None},
        )
        input_data = {
            inp["name"]: inp["inSource"]
            for inp in mapping.get("WS_INPUTS", [])
            if inp.get("name") and inp.get("inSource") is not None
        }
        if not input_data:
            input_data = {"uprn": str(user_uprn)}

        # 4. Retrieve the result. Note P_USER_ID is deliberately absent here -
        #    the council's own site omits it on this call, and including it
        #    causes the service to reject the request.
        result = self._get_plugin(
            session,
            "getWSRResult",
            {**service_params, "P_INPUT_DATA": input_data},
        )

        output_data = result.get("WSR_VALUE", {}).get("OUTPUT_DATA", [])
        if not output_data:
            raise ValueError(
                f"No collection data returned for UPRN {user_uprn}: {result}"
            )

        # The service returns rendered HTML rather than structured data, so the
        # collection table has to be read out of it.
        soup = BeautifulSoup(output_data[0].get("VAL", ""), "html.parser")
        today = datetime.now()
        data: dict[str, list[dict[str, str]]] = {"bins": []}

        for row in soup.select("table.govuk-table tbody tr"):
            cells = [cell.get_text(strip=True) for cell in row.select("td")]
            if len(cells) < 2:
                continue
            raw_date, bin_type = cells[0], cells[1]
            collection_date = self._parse_collection_date(raw_date, today)
            data["bins"].append(
                {
                    "type": bin_type,
                    "collectionDate": collection_date.strftime(date_format),
                }
            )

        if not data["bins"]:
            raise ValueError(
                f"Collection table was empty for UPRN {user_uprn} - the council's "
                "output format may have changed."
            )

        data["bins"].sort(
            key=lambda b: datetime.strptime(b["collectionDate"], date_format)
        )
        return data
