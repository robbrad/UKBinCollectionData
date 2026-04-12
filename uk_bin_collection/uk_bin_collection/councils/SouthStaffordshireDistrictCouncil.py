from datetime import datetime

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    South Staffordshire Council — bin collection data is served by
    https://www.sstaffs.gov.uk/where-i-live?objectId=<UPRN>.

    The older `?uprn=<UPRN>` query parameter is a placeholder that returns
    the fallback "van collection" message for every property. The real
    calendar uses the `objectId` parameter (the same UPRN, just a
    different query key).

    UPRNs for the property lookup come from the AJAX endpoint
    POST /viewyourcollectioncalendar?ajax_form=1 with
    postcode=<POSTCODE>&_triggering_element_name=lookup_address_by_postcode.
    """

    BASE_URL = "https://www.sstaffs.gov.uk/where-i-live"

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        if not user_uprn:
            raise ValueError("South Staffordshire requires a UPRN (-u)")
        check_uprn(user_uprn)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(
            f"{self.BASE_URL}?objectId={user_uprn}",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, features="html.parser")
        bin_data = {"bins": []}

        section = soup.find("div", id="showCollectionDates")
        if not section:
            return bin_data

        # Handle the van-collection fallback cleanly.
        van_msg = section.find("p")
        if van_msg and "van collection" in van_msg.get_text().lower():
            return bin_data

        # The "next collection" card at the top of the section.
        next_date_el = section.find("p", class_="collection-date")
        next_type_el = section.find("p", class_="collection-type")
        if next_date_el and next_type_el:
            date_str = self._parse_date(next_date_el.get_text(strip=True))
            if date_str:
                for bin_type in self._split_bin_types(next_type_el.get_text(strip=True)):
                    bin_data["bins"].append(
                        {"type": bin_type, "collectionDate": date_str}
                    )

        # Subsequent collections are listed in a two-column table.
        table = section.find("table", class_="leisure-table")
        if table:
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) != 2:
                    continue
                bin_type_text = cells[0].get_text(strip=True)
                date_text = cells[1].get_text(strip=True)
                if not bin_type_text or not date_text:
                    continue
                date_str = self._parse_date(date_text)
                if not date_str:
                    continue
                for bin_type in self._split_bin_types(bin_type_text):
                    bin_data["bins"].append(
                        {"type": bin_type, "collectionDate": date_str}
                    )

        # De-dupe (next collection card may repeat the first table row).
        seen = set()
        unique = []
        for entry in bin_data["bins"]:
            key = (entry["type"], entry["collectionDate"])
            if key not in seen:
                seen.add(key)
                unique.append(entry)
        unique.sort(
            key=lambda x: datetime.strptime(x["collectionDate"], date_format)
        )
        bin_data["bins"] = unique
        return bin_data

    @staticmethod
    def _parse_date(text):
        """Parse strings like 'Tuesday, 14 April 2026' -> '14/04/2026'."""
        cleaned = text.replace(",", " ").strip()
        parts = cleaned.split()
        if len(parts) < 4:
            return None
        day_num, month, year = parts[1], parts[2], parts[3]
        try:
            parsed = datetime.strptime(
                f"{day_num} {month} {year}", "%d %B %Y"
            )
        except ValueError:
            return None
        return parsed.strftime(date_format)

    @staticmethod
    def _split_bin_types(text):
        """Split composite types like 'Recycling & Garden waste' into
        ['Recycling', 'Garden waste'] so the app can show icons for each."""
        parts = [p.strip() for p in text.replace(" and ", " & ").split("&")]
        return [p for p in parts if p]
