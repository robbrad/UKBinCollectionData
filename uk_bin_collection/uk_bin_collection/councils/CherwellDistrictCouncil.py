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

        # Make the GET request with proper headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(URI, headers=headers)

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

        # Find the bin collection results section
        results_div = soup.find("div", class_="bin-collection-results")
        if not results_div:
            return bindata

        tasks_div = results_div.find("div", class_="bin-collection-results__tasks")
        if not tasks_div:
            return bindata

        # Find all bin collection items
        for item in tasks_div.find_all("li", class_="list__item"):
            # Extract bin type from heading
            heading = item.find("h3", class_="bin-collection-tasks__heading")
            if not heading:
                continue
                
            # Get the bin type text, excluding visually hidden spans
            bin_type = ""
            for text_node in heading.find_all(text=True):
                parent = text_node.parent
                if not (parent.name == "span" and "visually-hidden" in parent.get("class", [])):
                    bin_type += text_node.strip()
            
            if not bin_type:
                continue

            # Extract collection date
            date_tag = item.find("p", class_="bin-collection-tasks__date")
            if not date_tag:
                continue
                
            collection_date = date_tag.text.strip()

            dict_data = {
                "type": bin_type,
                "collectionDate": get_full_date(collection_date),
            }
            bindata["bins"].append(dict_data)

        # Sort bins by collection date
        if bindata["bins"]:
            bindata["bins"].sort(
                key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
            )

        return bindata
