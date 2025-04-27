import json
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

    def extract_dates(self, date_string: str) -> list:
        """
        Extract dates from strings like "01/05/2025, and then 15/05/2025"
        Returns list of datetime objects
        """
        date_string = date_string.replace("and then", ",")
        date_parts = [part.strip() for part in date_string.split(",") if part.strip()]

        dates = []
        for part in date_parts:
            try:
                date_obj = datetime.strptime(part, "%d/%m/%Y")
                dates.append(date_obj)
            except ValueError:
                continue

        return dates

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        url = f"https://my.melton.gov.uk/set-location?id={user_uprn}&redirect=collections&rememberloc="
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        collections = []

        # Find all box items
        box_items = soup.find_all("li", class_=lambda x: x and x.startswith("box-item"))

        for box in box_items:
            bin_type = box.find("h2")
            if (
                bin_type and "Missed bin" not in bin_type.text
            ):  # Skip the "Missed bin" section
                bin_name = bin_type.text.strip()

                # Find the strong tag containing dates
                dates_element = box.find("strong")
                if dates_element:
                    dates_text = dates_element.text.strip()
                    # Use self.extract_dates instead of extract_dates
                    collection_dates = self.extract_dates(dates_text)

                    # Add each date for this bin type to collections
                    for date in collection_dates:
                        collections.append((bin_name, date))

        # Sort the collections by date
        ordered_data = sorted(collections, key=lambda x: x[1])

        # Format the data as required
        data = {"bins": []}
        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        print(json.dumps(data, indent=2))

        return data
