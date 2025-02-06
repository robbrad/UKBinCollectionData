from datetime import datetime, timedelta

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

        URI = f"https://www.cherwell.gov.uk/homepage/129/bin-collection-search?uprn={user_uprn}"

        # Make the GET request
        response = requests.get(URI)

        soup = BeautifulSoup(response.text, "html.parser")

        def get_full_date(date_str):
            # Get the current year
            current_year = datetime.today().year

            date_str = remove_ordinal_indicator_from_date_string(date_str)

            # Convert the input string to a datetime object (assuming the current year first)
            date_obj = datetime.strptime(f"{date_str} {current_year}", "%d %B %Y")

            # If the date has already passed this year, use next year
            if date_obj < datetime.today():
                date_obj = datetime.strptime(
                    f"{date_str} {current_year + 1}", "%d %B %Y"
                )

            return date_obj.strftime(date_format)  # Return in YYYY-MM-DD format

        # print(soup)

        div = soup.find("div", class_="bin-collection-results__tasks")

        for item in div.find_all("li", class_="list__item"):
            # Extract bin type
            bin_type_tag = item.find("h3", class_="bin-collection-tasks__heading")
            bin_type = (
                "".join(bin_type_tag.find_all(text=True, recursive=False)).strip()
                if bin_type_tag
                else "Unknown Bin"
            )

            # Extract collection date
            date_tag = item.find("p", class_="bin-collection-tasks__date")
            collection_date = date_tag.text.strip() if date_tag else "Unknown Date"

            dict_data = {
                "type": bin_type,
                "collectionDate": get_full_date(collection_date),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
