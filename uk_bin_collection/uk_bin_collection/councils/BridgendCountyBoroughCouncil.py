import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

BASE_URL = "https://bridgendportal.azurewebsites.net"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36"
    ),
}


class CouncilClass(AbstractGetBinDataClass):
    """
    Bridgend County Borough Council bin collections via the PlanB
    Environmental portal at bridgendportal.azurewebsites.net.

    Resolution order:
        1. explicit UPRN (``uprn`` kwarg)
        2. ``postcode`` + optional ``paon`` resolved through the portal
           address search
    """

    def _search_properties(self, session: requests.Session, query: str) -> list:
        """POST the search form and return a list of (uprn, address) tuples."""
        payload = {
            "id": "",
            "aj": "true",
            "if": "",
            "gac": "FALSE",
            "search_property": query,
            "search_subpremise": "",
            "search_streetnumber": "",
            "search_locality": "",
            "search_postalcode": "",
        }
        resp = session.post(
            f"{BASE_URL}/property/",
            data=payload,
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()

        data = resp.json()
        if data.get("status") != "OK":
            return []

        soup = BeautifulSoup(data.get("result", ""), "html.parser")
        results = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            match = re.search(r"/property/(\d+)", href)
            if match:
                uprn = match.group(1)
                address = link.get_text(strip=True)
                results.append((uprn, address))
        return results

    def _resolve_uprn(self, session: requests.Session, postcode: str, paon: str) -> str:
        """Resolve postcode + house number to a UPRN via the portal search."""
        properties = self._search_properties(session, postcode)
        if not properties:
            raise ValueError(f"No properties found for postcode {postcode}")

        if not paon:
            return properties[0][0]

        target = paon.strip().lower()

        # Exact match: address starts with house number/name
        for uprn, address in properties:
            addr_lower = address.lower()
            if addr_lower.startswith(target + " ") or addr_lower.startswith(target + ","):
                return uprn

        # Numeric prefix match: "1" matches "1 Heronston Lane"
        if target.isdigit():
            for uprn, address in properties:
                addr_match = re.match(r"^(\d+)\b", address)
                if addr_match and addr_match.group(1) == target:
                    return uprn

        # Substring fallback
        for uprn, address in properties:
            if target in address.lower():
                return uprn

        # No match — fall back to first result
        return properties[0][0]

    def _get_collections(self, session: requests.Session, uprn: str) -> list:
        """Fetch the property page and parse the collection table."""
        resp = session.get(
            f"{BASE_URL}/property/{uprn}",
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", class_="table")
        if not table:
            raise ValueError(
                f"No collection table found for UPRN {uprn}. "
                "The property may not have active services."
            )

        bins = []
        for row in table.find("tbody").find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            service_cell = cells[0]
            # Get the service name from the first <a> only (skip sub-links)
            link = service_cell.find("a", class_="toggle-events")
            if link:
                bin_type = link.get_text(strip=True)
            else:
                # Fallback: first link or direct text
                link = service_cell.find("a")
                bin_type = link.get_text(strip=True) if link else service_cell.get_text(strip=True)

            # The "Next Service" cell contains a <span class="table-label">
            # followed by the date text. Strip the label span to get just the date.
            next_cell = cells[3]
            label_span = next_cell.find("span", class_="table-label")
            if label_span:
                label_span.decompose()
            next_service_text = next_cell.get_text(strip=True)
            if not next_service_text:
                continue

            # Extract dd/mm/yyyy date from the text
            date_match = re.search(r"\d{2}/\d{2}/\d{4}", next_service_text)
            if not date_match:
                continue

            try:
                parsed_date = datetime.strptime(date_match.group(), "%d/%m/%Y")
                collection_date = parsed_date.strftime(date_format)
            except ValueError:
                continue

            bins.append({
                "type": bin_type,
                "collectionDate": collection_date,
            })

        return bins

    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}

        uprn = kwargs.get("uprn")
        postcode = kwargs.get("postcode")
        paon = kwargs.get("paon")

        session = requests.Session()

        if not uprn:
            if not postcode:
                raise ValueError(
                    "Bridgend requires either a UPRN or a postcode."
                )
            check_postcode(postcode)
            uprn = self._resolve_uprn(session, postcode, paon or "")

        data["bins"] = self._get_collections(session, uprn)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], date_format)
        )

        return data
