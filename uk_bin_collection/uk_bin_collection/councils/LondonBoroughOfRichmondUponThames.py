from datetime import datetime
import re
import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):

    BASE_URL = "https://www.richmond.gov.uk/my_richmond"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) "
            "Gecko/20100101 Firefox/147.0"
        ),
        "Accept": "text/html,*/*",
        "Referer": "https://www.richmond.gov.uk/",
    }

    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        url = f"{self.BASE_URL}?pid={uprn}"

        r = requests.get(url, headers=self.HEADERS, timeout=30)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        container = soup.select_one("div.my-item.my-waste")
        if not container:
            raise ValueError("Waste container not found")

        bindata = {"bins": []}

        # iterate h4 -> ul pairs
        for h4 in container.find_all("h4"):
            bin_type = h4.get_text(strip=True)

            ul = h4.find_next_sibling("ul")
            if not ul:
                continue

            for li in ul.find_all("li"):
                text = li.get_text(" ", strip=True)

                # ignore non-collection rows
                if "No collection" in text:
                    continue

                date = self._extract_date(text)
                if not date:
                    continue

                bindata["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": date,
                    }
                )

        if not bindata["bins"]:
            raise ValueError("No bin data found")

        return bindata

    # --------------------------------------------------

    def _extract_date(self, text: str) -> str | None:
        """
        Extracts 'Wednesday 21 January 2026' → dd/MM/yyyy
        """
        try:
            dt = datetime.strptime(text.strip(), "%A %d %B %Y")
            return dt.strftime(date_format)
        except ValueError:
            return None
