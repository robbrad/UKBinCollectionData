import re
from datetime import datetime
from urllib.parse import quote

import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

ADDRESS_SEARCH_URL = "https://www.ashfield.gov.uk/api/address/search/{postcode}"
COLLECTIONS_URL = "https://www.ashfield.gov.uk/api/address/collections/{uprn}"
REQUEST_TIMEOUT_SECONDS = 30
COUNCIL_DATE_FORMAT = "%d/%m/%Y %H:%M:%S"


def select_uprn(results: list, paon: str) -> str:
    """Return the UPRN of the one address whose line starts with the house name/number.

    The match is anchored at the start of the address and must end on a word
    boundary, so "1" matches "1, Penrose Court" but not "10, ..." or "1A, ...".
    Raises ValueError if zero or several addresses match.
    """
    wanted = re.compile(rf"^{re.escape(paon.strip())}(?!\w)", re.IGNORECASE)
    matches = []
    for result in results:
        address = result.get("DPA", {})
        # "1, PENROSE COURT, ..." -> "1 PENROSE COURT ..." so "7 Penrose Court" also works
        text = re.sub(r"\s*,\s*", " ", address.get("ADDRESS", "")).strip()
        if wanted.match(text) and address.get("UPRN"):
            matches.append((address["ADDRESS"], address["UPRN"]))
    if len(matches) != 1:
        listed = "; ".join(address for address, _ in matches) or "none"
        raise ValueError(
            f"Expected exactly one address starting with '{paon}', "
            f"found {len(matches)}: {listed}"
        )
    return matches[0][1]


def parse_collections(collections: list) -> dict:
    """Convert the council's collections list to the standard bins dict."""
    bins = []
    for collection in collections:
        collection_date = datetime.strptime(collection["date"], COUNCIL_DATE_FORMAT)
        bins.append(
            {
                "type": collection["service"],
                "collectionDate": collection_date.strftime(date_format),
            }
        )
    if not bins:
        raise ValueError("The council returned no collection dates for this address")
    return {"bins": bins}


class CouncilClass(AbstractGetBinDataClass):
    """
    Ashfield publishes its bin calendar through two plain JSON endpoints behind
    its own page (postcode -> addresses, UPRN -> collections), so no browser is needed.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_paon(user_paon)
        check_postcode(user_postcode)

        response = requests.get(
            ADDRESS_SEARCH_URL.format(postcode=quote(user_postcode.strip())),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        uprn = select_uprn(response.json().get("results") or [], user_paon)

        response = requests.get(
            COLLECTIONS_URL.format(uprn=uprn), timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            raise ValueError(f"The council reported no success for UPRN lookup: {data}")
        return parse_collections(data.get("collections") or [])
