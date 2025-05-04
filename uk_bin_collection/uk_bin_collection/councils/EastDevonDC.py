import re
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    baseclass. They can also override some
    operations with a default implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:

        try:
            user_uprn = kwargs.get("uprn")
            check_uprn(user_uprn)
            url = f"https://eastdevon.gov.uk/recycling-and-waste/recycling-waste-information/when-is-my-bin-collected/future-collections-calendar/?UPRN={user_uprn}"
            if not user_uprn:
                # This is a fallback for if the user stored a URL in old system. Ensures backwards compatibility.
                url = kwargs.get("url")
        except Exception as e:
            raise ValueError(f"Error getting identifier: {str(e)}")

        # Make a BS4 object
        page = requests.get(url)
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}
        month_class_name = 'class="eventmonth"'
        regular_collection_class_name = "collectiondate regular-collection"
        holiday_collection_class_name = "collectiondate bankholiday-change"
        regex_string = "[^0-9]"

        calendar_collection = soup.find("ol", {"class": "nonumbers news collections"})
        calendar_list = calendar_collection.find_all("li")
        current_month = ""
        current_year = ""

        for element in calendar_list:
            element_tag = str(element)
            if month_class_name in element_tag:
                current_month = datetime.strptime(element.text, "%B %Y").strftime("%m")
                current_year = datetime.strptime(element.text, "%B %Y").strftime("%Y")
            elif regular_collection_class_name in element_tag:
                week_value = element.find_next(
                    "span", {"class": f"{regular_collection_class_name}"}
                )
                day_of_week = re.sub(regex_string, "", week_value.text).strip()
                collection_date = datetime(
                    int(current_year), int(current_month), int(day_of_week)
                ).strftime(date_format)
                collections = week_value.find_next_siblings("span")
                for item in collections:
                    x = item.text
                    bin_type = item.text.strip()
                    if len(bin_type) > 1:
                        dict_data = {
                            "type": bin_type,
                            "collectionDate": collection_date,
                        }
                        data["bins"].append(dict_data)
            elif holiday_collection_class_name in element_tag:
                week_value = element.find_next(
                    "span", {"class": f"{holiday_collection_class_name}"}
                )
                day_of_week = re.sub(regex_string, "", week_value.text).strip()
                collection_date = datetime(
                    int(current_year), int(current_month), int(day_of_week)
                ).strftime(date_format)
                collections = week_value.find_next_siblings("span")
                for item in collections:
                    x = item.text
                    bin_type = item.text.strip()
                    if len(bin_type) > 1:
                        dict_data = {
                            "type": bin_type + " (bank holiday replacement)",
                            "collectionDate": collection_date,
                        }
                        data["bins"].append(dict_data)
        return data
