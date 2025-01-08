from datetime import datetime, timedelta
from typing import Any, Dict

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def get_next_weekday(self, day_name: str) -> str:
        days_of_week = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        today = datetime.today()
        target_day = days_of_week.index(day_name)
        days_until_target = (target_day - today.weekday() + 7) % 7
        if days_until_target == 0:
            days_until_target = 7  # Next occurrence should be next week
        next_weekday = today + timedelta(days=days_until_target)
        return next_weekday.strftime("%d/%m/%Y")

    def parse_data(self, page: Any, **kwargs: Any) -> Dict[str, Any]:
        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}
        # Find the section with the title "Bins, rubbish & recycling"
        h2_header = soup.find("h2", id="rubbish-header")

        # Mapping original titles to new titles
        title_mapping = {
            "Next rubbish collection date": "Rubbish",
            "Next recycling collection date": "Recycling",
            "Food waste collection": "Food Waste",
            "Garden waste collection": "Garden Waste",
        }

        # Extract the list items following this section
        if h2_header:
            list_items = h2_header.find_next("ul", class_="list-group").find_all("li")

            extracted_data = {}
            for item in list_items:
                header = item.find("h3")
                if header:
                    key = header.text.strip()
                    date = item.find("p").strong.text.strip()
                    extracted_data[key] = date
                else:
                    # Special handling for garden waste collection
                    if "Garden waste collection" in item.text:
                        key = "Garden waste collection"
                        date = item.find_all("strong")[1].text.strip()
                        extracted_data[key] = date

            print("Extracted data:", extracted_data)

            # Transform the data to the required schema
            bin_data = {"bins": []}

            for key, value in extracted_data.items():
                if value.startswith("Every"):
                    # Extract the day name
                    day_name = value.split()[1]
                    # Convert to the next occurrence of that day
                    formatted_date = self.get_next_weekday(day_name)
                else:
                    # Convert date format from "Tuesday 28 May 2024" to "28/05/2024"
                    try:
                        date_obj = datetime.strptime(value, "%A %d %B %Y")
                    except:
                        continue
                    formatted_date = date_obj.strftime("%d/%m/%Y")

                bin_entry = {
                    "type": title_mapping.get(key, key),
                    "collectionDate": formatted_date,
                }

                bin_data["bins"].append(bin_entry)

            return bin_data
        else:
            print("Section not found")
            return data
