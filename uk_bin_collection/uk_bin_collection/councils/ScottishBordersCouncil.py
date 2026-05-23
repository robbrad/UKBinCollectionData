import json
import re

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    BASE_URL = "https://scotborders-live-portal.bartecmunicipal.com/Embeddable/CollectionCalendar"

    def _get_csrf_token(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        token = soup.find("input", {"name": "__RequestVerificationToken"})
        if not token:
            raise ValueError("Could not find CSRF token on the page.")
        value = token.get("value")
        if not value:
            raise ValueError("CSRF token element found but value is empty")
        return value

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon") or kwargs.get("house_number")
        check_postcode(user_postcode)

        bindata = {"bins": []}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
        }
        form_headers = {
            "Referer": self.BASE_URL,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        session = requests.Session()
        session.headers.update(headers)

        # Step 1: GET the calendar page to obtain the CSRF token
        response = session.get(self.BASE_URL, timeout=30)
        response.raise_for_status()
        csrf_token = self._get_csrf_token(response.text)

        # Step 2: POST the postcode to the SearchPostcode handler
        # The Bartec portal renders addresses as a Syncfusion DropDownList
        # with a JSON dataSource embedded in a <script> tag.
        response = session.post(
            f"{self.BASE_URL}?handler=SearchPostcode",
            data={
                "SelectedPostcode": user_postcode,
                "__RequestVerificationToken": csrf_token,
            },
            headers=form_headers,
            timeout=30,
        )
        response.raise_for_status()

        # Extract address list from the DropDownList dataSource JSON
        address_match = re.search(
            r"DropDownList\(\{[^}]*\"dataSource\":\s*ejs\.data\.DataUtil\.parse\.isJson\((\[.*?\])\)",
            response.text,
            re.DOTALL,
        )
        if not address_match:
            raise ValueError(
                f"No addresses found for postcode {user_postcode}. "
                "Please check the postcode is within Scottish Borders."
            )

        addresses = json.loads(address_match.group(1))

        # Find the right address: try Bartec UPRN first, then match by
        # house number/name (paon) so our API's OS UPRN -> postcode+number
        # fallback chain works.
        def _safe_uprn(addr):
            try:
                return str(int(addr.get("UPRN", 0)))
            except (ValueError, TypeError):
                return None

        selected_uprn = None
        if user_uprn:
            for addr in addresses:
                addr_uprn = _safe_uprn(addr)
                if addr_uprn and addr_uprn == str(user_uprn):
                    selected_uprn = addr_uprn
                    break

        if not selected_uprn and user_paon:
            paon_lower = user_paon.lower().strip()
            for addr in addresses:
                premises = addr.get("Premises", "").lower().strip()
                if premises.startswith(paon_lower) or paon_lower in premises:
                    selected_uprn = _safe_uprn(addr)
                    if selected_uprn:
                        break

        if not selected_uprn and addresses:
            selected_uprn = _safe_uprn(addresses[0])

        if not selected_uprn:
            raise ValueError(
                f"No addresses found for postcode {user_postcode}."
            )

        user_uprn = selected_uprn

        # Get fresh CSRF token from the search results page
        csrf_token = self._get_csrf_token(response.text)

        # Step 3: POST to select the premises by UPRN
        response = session.post(
            f"{self.BASE_URL}?handler=SelectPrem",
            data={
                "SelectedPostcode": user_postcode,
                "SelectedPremises": str(user_uprn),
                "__RequestVerificationToken": csrf_token,
            },
            headers=form_headers,
            timeout=30,
        )
        response.raise_for_status()

        # Step 4: Extract calendar events from the rendered page.
        # The page contains two isJson([...]) calls:
        #   1st = address dropdown data (DropDownList)
        #   2nd = calendar events (Schedule eventSettings.dataSource)
        # We need the second one which has "Subject" keys.
        all_matches = re.findall(
            r"DataUtil\.parse\.isJson\((\[.*?\])\)",
            response.text,
            re.DOTALL,
        )

        events = []
        for raw_json in all_matches:
            try:
                parsed = json.loads(raw_json)
            except json.JSONDecodeError:
                continue
            if parsed and isinstance(parsed[0], dict) and "Subject" in parsed[0]:
                events = parsed
                break

        if not events:
            raise ValueError(
                "No upcoming collections found for this address. "
                "The council may not have published schedules yet."
            )

        for event in events:
            subject = event.get("Subject", "")
            start_time = event.get("StartTime", "")
            if not subject or not start_time:
                continue

            bin_type = subject

            # Parse ISO date: "2026-05-26T00:00:00.000Z"
            try:
                collection_date = datetime.strptime(
                    start_time[:10], "%Y-%m-%d"
                )
            except ValueError:
                continue

            bindata["bins"].append(
                {
                    "type": bin_type,
                    "collectionDate": collection_date.strftime(date_format),
                }
            )

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        if not bindata["bins"]:
            raise ValueError("No upcoming collections found for this address")

        return bindata
