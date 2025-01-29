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

    def parse_data(self, page: str, **kwargs) -> dict:

        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)
        check_paon(user_paon)
        bindata = {"bins": []}

        URI = "http://collectiondates.eastlothian.gov.uk/ajax/your-calendar/load-streets-spring-2024.asp"

        payload = {
            "postcode": user_postcode,
        }

        headers = {
            "Referer": "http://collectiondates.eastlothian.gov.uk/your-calendar",
            "User-Agent": "Mozilla/5.0",
        }

        # Make the GET request
        response = requests.get(URI, headers=headers, params=payload)

        # Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the select dropdown
        select = soup.find("select", id="SelectStreet")

        # Find the option that contains "Flat 1"
        address = select.find("option", string=lambda text: text and user_paon in text)

        URI = "http://collectiondates.eastlothian.gov.uk/ajax/your-calendar/load-recycling-summer-2024.asp"

        payload = {
            "id": address["value"],
        }

        # Make the GET request
        response = requests.get(URI, headers=headers, params=payload)

        # Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract collection details
        calendar_items = soup.find_all("div", class_="calendar-item")
        for item in calendar_items:
            waste_label = item.find("div", class_="waste-label").text.strip()
            waste_value = item.find("div", class_="waste-value").find("h4").text.strip()

            try:
                collection_date = datetime.strptime(
                    remove_ordinal_indicator_from_date_string(waste_value),
                    "%A %d %B %Y",
                )
            except ValueError:
                continue

            dict_data = {
                "type": waste_label.replace(" is:", ""),
                "collectionDate": collection_date.strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
