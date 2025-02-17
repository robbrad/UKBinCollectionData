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

        URI = f"https://maps.epsom-ewell.gov.uk/myeebc.aspx?action=SetAddress&UniqueId={user_uprn}"

        # Make the GET request
        response = requests.get(URI)

        soup = BeautifulSoup(response.text, "html.parser")

        # print(soup)

        div = soup.find_all("div", class_="atPanelContent atAlt1 atLast")

        # print(div[1])

        panels = div[1].find_all("div", class_="atPanelData")

        # print(panels)

        def get_full_date(date_str):
            # Get the current year
            current_year = datetime.today().year

            # Convert the input string to a datetime object (assuming the current year first)
            date_obj = datetime.strptime(f"{date_str} {current_year}", "%A %d %B %Y")

            # If the date has already passed this year, use next year
            if date_obj < datetime.today():
                date_obj = datetime.strptime(
                    f"{date_str} {current_year + 1}", "%A %d %B %Y"
                )

            return date_obj.strftime(date_format)  # Return in YYYY-MM-DD format

        for panel in panels:
            bin_type_tag = panel.find("h4")  # Extracts bin type
            date_text = panel.find_all("td")  # Extracts collection date

            date_text = date_text[1]

            if bin_type_tag and date_text:
                bin_type = bin_type_tag.text.strip()
                try:
                    collection_date = date_text.text.strip().split(":")[1]
                except IndexError:
                    continue

                bin_type = (
                    (" ".join(bin_type.splitlines())).replace("  ", " ")
                ).lstrip()
                collection_date = (
                    (" ".join(collection_date.splitlines())).replace("  ", " ")
                ).lstrip()

                dict_data = {
                    "type": bin_type,
                    "collectionDate": get_full_date(collection_date),
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
