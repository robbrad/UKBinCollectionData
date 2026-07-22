import urllib3
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Council: Central Bedfordshire Council
    Council Website: https://www.centralbedfordshire.gov.uk/
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        
        check_uprn(user_uprn)

        api_url = f"https://www.centralbedfordshire.gov.uk/waste-and-recycling/waste-collection-schedule/view/{user_uprn}"
                 
        urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(api_url, timeout=30)

        if response.status_code != 200:
            raise ConnectionError(f"Failed to fetch data from {api_url}")

        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}
        collection_days = soup.find_all("li", class_="waste-collection__day")

        for collection in collection_days:
            date_element = collection.find("time")
            if date_element and date_element.has_attr('datetime'):
                date_str = date_element['datetime']
                # Using the date_format variable imported from common
                collection_date = datetime.strptime(date_str, "%d-%m-%Y").strftime(date_format)
            else:
                raise ValueError("Could not find a valid date element for collection day.")

            type_element = collection.find("span", class_="waste-collection__day--type")
            if type_element:
                raw_type = type_element.text.strip().lower()
            else:
                raise ValueError("Could not find a valid type element for collection day.")
                
            # Map the raw strings back to the original HA sensor formats
            extracted_bins = []
            if "food" in raw_type:
                extracted_bins.append("Food waste")
            if "garden" in raw_type:
                extracted_bins.append("Garden waste")
            if "recycling" in raw_type:
                extracted_bins.append("Recycling")
            if "refuse" in raw_type or "black bin" in raw_type:
                extracted_bins.append("Refuse (black bin)")

            if not extracted_bins:
                raise ValueError(f"Unrecognized bin type found: {raw_type}")

            # Append isolated bin types, checking for duplicates
            for bin_type in extracted_bins:
                dict_data = {
                    "type": bin_type,
                    "collectionDate": collection_date,
                }
                if dict_data not in data["bins"]:
                    data["bins"].append(dict_data)

        return data
