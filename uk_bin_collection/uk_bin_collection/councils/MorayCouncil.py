import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Moray Council bin collection scraper.
    Parses the annual calendar view which encodes bin types as CSS classes
    on day divs within month containers.
    """

    BIN_TYPE_MAP = {
        "B": "Brown Bin",
        "O": "Glass Container",
        "G": "Green Bin",
        "P": "Purple Bin",
        "C": "Blue Bin",
    }

    def _resolve_property_id(self, postcode: str, paon: str) -> str:
        """Search Moray's postcode lookup to find the internal property ID."""
        search_url = "https://bindayfinder.moray.gov.uk/refuse_roads.php"
        response = requests.get(
            search_url,
            params={"pcode": postcode},
            timeout=30,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", href=re.compile(r"disp_bins\.php\?id="))

        if not links:
            raise ValueError(f"No properties found for postcode: {postcode}")

        # Try to match by house number/name
        if paon:
            paon_lower = paon.strip().lower()
            num_match = re.match(r"^(\d+)", paon_lower)

            for link in links:
                link_text = link.get_text(strip=True).lower()
                # Exact start match
                if link_text.startswith(paon_lower):
                    return re.search(r"id=(\d+)", link["href"]).group(1)
                # House number match
                if num_match:
                    link_num = re.match(r"^(\d+)", link_text)
                    if link_num and link_num.group(1) == num_match.group(1):
                        return re.search(r"id=(\d+)", link["href"]).group(1)

        # Fallback: first property
        return re.search(r"id=(\d+)", links[0]["href"]).group(1)

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        bindata = {"bins": []}

        property_id = None

        # If postcode is available, resolve via Moray's own search
        # (Moray uses internal IDs, not real UPRNs)
        if user_postcode:
            property_id = self._resolve_property_id(user_postcode, user_paon or "")
        elif user_uprn:
            # Legacy: direct property ID passed as UPRN
            property_id = str(user_uprn).zfill(8)

        if not property_id:
            raise ValueError("Either postcode or property ID (as UPRN) required")

        property_id = property_id.zfill(8)
        year = datetime.today().year

        url = f"https://bindayfinder.moray.gov.uk/cal_{year}_view.php?id={property_id}"
        response = requests.get(url, timeout=30)

        if response.status_code != 200:
            return bindata

        soup = BeautifulSoup(response.text, "html.parser")
        today = datetime.today().date()

        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]

        for month_container in soup.find_all("div", class_="month-container"):
            header = month_container.find("div", class_="month-header")
            if not header or not header.find("h2"):
                continue
            month_name = header.find("h2").text.strip()
            if month_name not in month_names:
                continue
            month_num = month_names.index(month_name) + 1

            days_container = month_container.find("div", class_="days-container")
            if not days_container:
                continue

            for day_div in days_container.find_all("div"):
                css_classes = day_div.get("class", [])

                if "blank" in css_classes:
                    continue

                day_text = day_div.text.strip()
                if not day_text or not day_text.isdigit():
                    continue
                day_num = int(day_text)

                for css_class in css_classes:
                    if css_class in ("blank", "day-name", ""):
                        continue

                    for char in css_class:
                        if char in self.BIN_TYPE_MAP:
                            try:
                                collection_date = datetime(year, month_num, day_num).date()
                                if collection_date >= today:
                                    bindata["bins"].append({
                                        "type": self.BIN_TYPE_MAP[char],
                                        "collectionDate": collection_date.strftime(date_format),
                                    })
                            except ValueError:
                                continue

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
