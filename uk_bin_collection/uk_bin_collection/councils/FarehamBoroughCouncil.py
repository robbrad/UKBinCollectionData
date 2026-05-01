import requests
from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


BIN_TYPES = {"refuse": "Refuse", "recycle": "Recycling", "garden": "Garden Waste"}


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        url = f"https://www.fareham.gov.uk/bincalendar/intro.aspx?ref={uprn}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, features="html.parser")
        today = datetime.now()
        data = {"bins": []}

        for table in soup.find_all("table"):
            caption = table.find("caption")
            if not caption:
                continue
            month_str = caption.get_text(strip=True)
            try:
                month_date = datetime.strptime(month_str, "%B %Y")
            except ValueError:
                continue

            for td in table.find_all("td"):
                classes = td.get("class", [])
                day_text = td.get_text(strip=True)
                if not day_text or not day_text.isdigit():
                    continue
                day = int(day_text)
                try:
                    collection_date = month_date.replace(day=day)
                except ValueError:
                    continue
                if collection_date.date() < today.date():
                    continue
                for css_class in classes:
                    if css_class in BIN_TYPES:
                        data["bins"].append(
                            {
                                "type": BIN_TYPES[css_class],
                                "collectionDate": collection_date.strftime(
                                    date_format
                                ),
                            }
                        )

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
