import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Comhairle nan Eilean Siar (Western Isles Council).

    Area-based collections with no postcode lookup. The user provides a
    village, street, or area name via the paon parameter. The scraper
    searches the council's schedule pages to find matching routes and
    returns upcoming collection dates for all bin types.

    Lewis & Harris bin types:
      - Organic Food & Garden Waste / Mixed Recycling (Blue Bin)  - 3-weekly
      - Non-Recyclable Waste (Grey bin, purple sticker)           - 3-weekly
      - Glass (Green Bin)                                         - 9-weekly

    Uist & Barra bin types:
      - Residual Waste (Black Bin)                - fortnightly
      - Recycling - Paper/Card (Green sticker)    - fortnightly (alternating)
      - Recycling - Plastic/Tin (Blue sticker)    - fortnightly (alternating)
    """

    BASE_URL = "https://www.cne-siar.gov.uk"

    # Lewis & Harris schedule pages: (bin_type_label, base_path, day_slugs)
    LH_SCHEDULES = [
        (
            "Organic Food & Garden Waste / Mixed Recycling (Blue Bin)",
            "/bins-and-recycling/waste-recycling-collections-lewis-and-harris"
            "/organic-food-and-garden-waste-and-mixed-recycling-blue-bin",
            ["monday-collections", "tuesday-collections",
             "wednesday-collections", "thursday-collections",
             "friday-collections"],
        ),
        (
            "Non-Recyclable Waste (Grey Bin)",
            "/bins-and-recycling/waste-recycling-collections-lewis-and-harris"
            "/non-recyclable-waste-grey-bin-purple-sticker",
            ["monday-collections", "tuesday-collections",
             "wednesday-collections", "thursday-collections",
             "friday-collections"],
        ),
        (
            "Glass (Green Bin)",
            "/bins-and-recycling/waste-recycling-collections-lewis-and-harris"
            "/glass-green-bin-collections",
            ["thursday-collections", "friday-collections"],
        ),
    ]

    # Uist & Barra schedule pages: (bin_type_label, path, day_slugs)
    # Residual uses tables with simple date cells.
    # Recycling uses tables with Paper/Card and Plastic/Tin sub-types.
    UB_RESIDUAL = (
        "Residual Waste (Black Bin)",
        "/bins-and-recycling/uist-and-barra"
        "/waste-recycling-collections-uist-and-barra/residual-bins-black-bins",
        ["tuesday-collections", "thursday-collections"],
    )

    UB_RECYCLING = (
        None,  # bin type determined per-cell (Paper/Card or Plastic/Tin)
        "/bins-and-recycling/waste-recycling-collections-uist-and-barra"
        "/recycling-bins-blue-and-green",
        ["monday-collections", "tuesday-collections",
         "wednesday-collections"],
    )

    # HS1-HS2 = Stornoway/Lewis, HS3-HS5 = Harris,
    # HS6-HS8 = Uist, HS9 = Barra. If a postcode is provided we can
    # skip one region's pages entirely, halving HTTP requests.
    LH_POSTCODES = {"HS1", "HS2", "HS3", "HS4", "HS5"}
    UB_POSTCODES = {"HS6", "HS7", "HS8", "HS9"}

    def parse_data(self, page: str, **kwargs) -> dict:
        user_paon = kwargs.get("paon")
        if not user_paon:
            raise ValueError(
                "A village, street, or area name is required (paon parameter). "
                "Examples: 'Back', 'Leverburgh', 'Castlebay', 'Manor', "
                "'Goathill', 'Balivanich'. Check your area at "
                "https://www.cne-siar.gov.uk/bins-and-recycling"
            )

        bindata = {"bins": []}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
        }
        session = requests.Session()
        session.headers.update(headers)

        search_term = user_paon.strip().lower()

        # Determine which region(s) to search based on postcode
        user_postcode = kwargs.get("postcode", "").strip().upper()
        pc_district = user_postcode[:3].rstrip() if user_postcode else ""
        search_lh = not pc_district or pc_district in self.LH_POSTCODES
        search_ub = not pc_district or pc_district in self.UB_POSTCODES

        # Search Lewis & Harris accordion-style pages
        if search_lh:
            for bin_type, base_path, day_slugs in self.LH_SCHEDULES:
                for slug in day_slugs:
                    url = f"{self.BASE_URL}{base_path}/{slug}"
                    try:
                        self._parse_lh_accordion_page(
                            session, url, bin_type, search_term, bindata
                        )
                    except Exception:
                        continue

        # Search Uist & Barra table-style pages - Residual
        if search_ub:
            res_label, res_path, res_slugs = self.UB_RESIDUAL
            for slug in res_slugs:
                url = f"{self.BASE_URL}{res_path}/{slug}"
                try:
                    self._parse_ub_table_page(
                        session, url, res_label, search_term, bindata,
                        is_recycling=False,
                    )
                except Exception:
                    continue

            # Search Uist & Barra table-style pages - Recycling
            _, rec_path, rec_slugs = self.UB_RECYCLING
            for slug in rec_slugs:
                url = f"{self.BASE_URL}{rec_path}/{slug}"
                try:
                    self._parse_ub_table_page(
                        session, url, None, search_term, bindata,
                        is_recycling=True,
                    )
                except Exception:
                    continue

        if not bindata["bins"]:
            raise ValueError(
                f"No collection area found matching '{user_paon}'. "
                "Try a village name (e.g. 'Back', 'Leverburgh', 'Castlebay') "
                "or street name (e.g. 'Goathill', 'Manor'). "
                "Check https://www.cne-siar.gov.uk/bins-and-recycling"
            )

        # De-duplicate and sort
        seen = set()
        unique_bins = []
        for b in bindata["bins"]:
            key = (b["type"], b["collectionDate"])
            if key not in seen:
                seen.add(key)
                unique_bins.append(b)

        unique_bins.sort(
            key=lambda x: datetime.strptime(
                x.get("collectionDate"), date_format
            )
        )
        bindata["bins"] = unique_bins
        return bindata

    def _parse_lh_accordion_page(
        self,
        session: requests.Session,
        url: str,
        bin_type: str,
        search_term: str,
        bindata: dict,
    ):
        """Parse a Lewis & Harris accordion-style day page.

        Structure: .accordion-pane elements containing:
          - Area name in <button> text
          - Dates in <ol><li> items
          - Locations in <p> after <h4>
        """
        response = session.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        panes = soup.find_all(
            "div",
            class_=lambda c: c and "paragraph--type--localgov-accordion-pane" in c,
        )

        for pane in panes:
            # Get area name from button text
            button = pane.find("button")
            area_name = button.get_text(strip=True) if button else ""

            # Get body content with locations and dates
            body = pane.find(
                "div",
                class_=lambda c: c and "field--name-localgov-body-text" in c,
            )
            if not body:
                continue

            # Check if search term matches area name or locations text
            full_text = body.get_text(" ", strip=True).lower()
            area_lower = area_name.lower()

            if not self._matches_area(search_term, area_lower, full_text):
                continue

            # Extract dates from <ol><li> elements
            dates = []
            for li in body.find_all("li"):
                date_text = li.get_text(strip=True)
                parsed = self._parse_date_text(date_text)
                if parsed:
                    dates.append(parsed)

            now = datetime.now()
            for dt in dates:
                if dt >= now:
                    bindata["bins"].append(
                        {
                            "type": bin_type,
                            "collectionDate": dt.strftime(date_format),
                        }
                    )

    def _parse_ub_table_page(
        self,
        session: requests.Session,
        url: str,
        bin_type: str,
        search_term: str,
        bindata: dict,
        is_recycling: bool = False,
    ):
        """Parse a Uist & Barra table-style day page.

        Structure: <table> with rows containing:
          - First <td data-title="Area">: comma-separated locations
          - Subsequent <td>s: month columns with dates
          - For recycling: cells contain <strong>Paper/Card</strong> and
            <strong>Plastic/Tin</strong> sub-sections
        """
        response = session.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        tables = soup.find_all("table")
        for table in tables:
            # Get month headers
            headers = []
            thead = table.find("thead")
            if thead:
                for th in thead.find_all("th"):
                    headers.append(th.get_text(strip=True))

            # Month headers are typically: Area, May, June, etc.
            month_headers = headers[1:] if len(headers) > 1 else []

            rows = table.find("tbody")
            if not rows:
                continue

            for row in rows.find_all("tr"):
                cells = row.find_all("td")
                if not cells:
                    continue

                # First cell is the area
                area_cell = cells[0]
                area_text = area_cell.get_text(" ", strip=True).lower()

                if not self._matches_area(search_term, area_text, area_text):
                    continue

                # Parse date cells
                for i, cell in enumerate(cells[1:], start=0):
                    month_name = month_headers[i] if i < len(month_headers) else ""

                    if is_recycling:
                        # Recycling cells have Paper/Card and Plastic/Tin
                        self._parse_recycling_cell(
                            cell, month_name, bindata
                        )
                    else:
                        # Simple date cells
                        dates = self._parse_date_cell(cell, month_name)
                        now = datetime.now()
                        for dt in dates:
                            if dt >= now:
                                bindata["bins"].append(
                                    {
                                        "type": bin_type,
                                        "collectionDate": dt.strftime(
                                            date_format
                                        ),
                                    }
                                )

    def _parse_recycling_cell(
        self, cell, month_name: str, bindata: dict
    ):
        """Parse a Uist & Barra recycling cell that contains both
        Paper/Card and Plastic/Tin dates.

        HTML structure within each <td>:
          <p><strong>Paper/Card</strong><br>18th</p>
          <p><strong>Plastic/Tin</strong><br>4th</p>
        """
        now = datetime.now()

        # Each <p> in the cell contains one sub-type
        paragraphs = cell.find_all("p")
        for p in paragraphs:
            strong = p.find("strong")
            if not strong:
                continue

            sub_type_text = strong.get_text(strip=True).lower()
            if "paper" in sub_type_text or "card" in sub_type_text:
                sub_bin_type = "Recycling - Paper/Card (Green Sticker)"
            elif "plastic" in sub_type_text or "tin" in sub_type_text:
                sub_bin_type = "Recycling - Plastic/Tin (Blue Sticker)"
            else:
                continue

            # Get the date text (everything in the <p> except the <strong>)
            full_text = p.get_text(" ", strip=True)
            # Remove the sub-type label to get just dates
            date_text = full_text.replace(strong.get_text(strip=True), "").strip()

            dates = self._parse_dates_from_text(date_text, month_name)
            for dt in dates:
                if dt >= now:
                    bindata["bins"].append(
                        {
                            "type": sub_bin_type,
                            "collectionDate": dt.strftime(date_format),
                        }
                    )

    def _matches_area(
        self, search_term: str, area_name: str, locations_text: str
    ) -> bool:
        """Check if a search term matches an area name or location list.

        Uses word-boundary matching to avoid false positives (e.g.
        'Coll' should not match 'collection' but should match 'Coll,').
        """
        # Normalise: strip punctuation around words for matching
        pattern = r"(?<![a-z])" + re.escape(search_term) + r"(?![a-z])"

        if re.search(pattern, area_name, re.IGNORECASE):
            return True
        if re.search(pattern, locations_text, re.IGNORECASE):
            return True
        return False

    def _parse_date_text(self, text: str):
        """Parse a single date like 'April 13th' or 'May 4th' into a
        datetime. Dates on the council site don't include years, so we
        infer the year based on the current date."""
        # Remove ordinal suffixes
        cleaned = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text.strip())

        # Try parsing with current year first, then next year
        now = datetime.now()
        for year in [now.year, now.year + 1]:
            try:
                return datetime.strptime(f"{cleaned} {year}", "%B %d %Y")
            except ValueError:
                continue
        return None

    def _parse_date_cell(self, cell, month_name: str) -> list:
        """Parse a table cell containing dates like '12th, 26th' with
        a known month name from the column header."""
        text = cell.get_text(" ", strip=True)
        return self._parse_dates_from_text(text, month_name)

    def _parse_dates_from_text(self, text: str, month_name: str) -> list:
        """Parse multiple dates from text like '12th, 26th' given a
        month name. Returns list of datetime objects."""
        dates = []
        if not text or not month_name:
            return dates

        # Find all day numbers
        day_numbers = re.findall(r"(\d+)(?:st|nd|rd|th)?", text)
        now = datetime.now()

        for day_str in day_numbers:
            for year in [now.year, now.year + 1]:
                try:
                    dt = datetime.strptime(
                        f"{day_str} {month_name} {year}", "%d %B %Y"
                    )
                    dates.append(dt)
                    break
                except ValueError:
                    continue

        return dates
