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

        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        URI = f"https://www.west-dunbarton.gov.uk/recycling-and-waste/bin-collection-day/?uprn={user_uprn}"

        # Make the GET request
        response = requests.get(URI)

        soup = BeautifulSoup(response.content, "html.parser")

        # For each next-date class get the text within the date-string class
        schedule_details = soup.findAll("div", {"class": "round-info"})

        for item in schedule_details:
            schedule_date = item.find("span", {"class": "date-string"}).text.strip()
            schedule_type = item.find("div", {"class": "round-name"}).text.strip()
            # Format is 22 March 2023 - convert to date
            collection_date = datetime.strptime(schedule_date, "%d %B %Y").date()

            # If the type contains "Blue bin or bag" or "Blue" then set the type to "BLUE"
            if "bag" in schedule_type.lower() or "blue" in schedule_type.lower():
                dict_data = {
                    "type": "Blue",
                    "collectionDate": collection_date.strftime(date_format),
                }
                bindata["bins"].append(dict_data)

            # If the type contains "caddy" or "brown" then set the type to "BROWN"
            if "caddy" in schedule_type.lower() or "brown" in schedule_type.lower():
                dict_data = {
                    "type": "Brown",
                    "collectionDate": collection_date.strftime(date_format),
                }
                bindata["bins"].append(dict_data)

            # If the type contains "Non-Recyclable" then set the type to "BLACK", compare in lowecase
            if "non-recyclable" in schedule_type.lower():
                dict_data = {
                    "type": "Black",
                    "collectionDate": collection_date.strftime(date_format),
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
