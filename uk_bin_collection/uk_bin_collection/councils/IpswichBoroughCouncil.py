import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    IBC_SUPPORTED_BINS_DICT = {
        "black": "Black Refuse",
        "blue": "Blue Recycling",
        "brown": "Brown Garden Waste",
        "green": "Green Recycling",
        "food": "Food Caddy",
    }

    IBC_ENDPOINT = "https://app.ipswich.gov.uk/bin-collection/"

    def parse_data(self, page: str, **kwargs) -> dict:

        user_paon = kwargs.get("paon")
        check_paon(user_paon)

        form_data = {"street-name": user_paon, "submit-button": ""}
        response = requests.post(self.IBC_ENDPOINT, data=form_data, timeout=10)
        soup = BeautifulSoup(response.content, features="html.parser")

        data = {"bins": []}

        dl = soup.find("dl", class_="ibc-calendar-grid")
        if not dl:
            return data

        for div in dl.find_all("div", recursive=False):
            dt = div.find("dt", class_="ibc-calendar-entry")
            dd = div.find("dd", class_="ibc-calendar-entry__details")
            if not (dt and dd):
                continue

            day = dt.find("div", class_="ibc-calendar-entry__day").get_text(strip=True)
            date_div = dt.find("div", class_="ibc-calendar-entry__date")
            date_num = date_div.contents[0].strip()
            month_year = dt.find("div", class_="ibc-calendar-entry__month").get_text(strip=True)

            date_obj = datetime.strptime(f"{day} {date_num} {month_year}", "%A %d %B %Y")
            collection_date = date_obj.strftime(date_format)

            for li in dd.find_all("li"):
                bin_class = li.get("class", [None])[0]
                if bin_class in self.IBC_SUPPORTED_BINS_DICT:
                    data["bins"].append({
                        "type": self.IBC_SUPPORTED_BINS_DICT[bin_class],
                        "collectionDate": collection_date,
                    })

        return data
