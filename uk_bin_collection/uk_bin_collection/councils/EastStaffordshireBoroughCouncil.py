import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

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

        bindata = {"bins": []}

        soup = BeautifulSoup(page.text, features="html.parser")

        current_year = datetime.now().year
        next_year = current_year + 1

        # Extract next collection
        next_collection_section = soup.find("div", class_="collection-next")
        if next_collection_section:
            next_collection_text = next_collection_section.find("h2").text.strip()
            date_match = re.search(
                r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), (\d+)(?:st|nd|rd|th)? (\w+)",
                next_collection_text,
            )
            if date_match:
                collection_date = f"{date_match.group(1)} {remove_ordinal_indicator_from_date_string(date_match.group(2))} {date_match.group(3)}"

                collection_date = datetime.strptime(collection_date, "%A %d %B")

                if (datetime.now().month == 12) and (collection_date.month == 1):
                    collection_date = collection_date.replace(year=next_year)
                else:
                    collection_date = collection_date.replace(year=current_year)

                # Get bin types
                bins = next_collection_section.find_all("div", class_="field__item")
                for bin_type in bins:
                    dict_data = {
                        "type": bin_type.text.strip(),
                        "collectionDate": collection_date.strftime(date_format),
                    }
                    bindata["bins"].append(dict_data)

        # Extract other collections
        other_collections = soup.find_all("li")
        for collection in other_collections:
            date_text = collection.contents[0].strip()
            date_match = re.search(
                r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), (\d+)(?:st|nd|rd|th)? (\w+)",
                date_text,
            )
            if date_match:
                collection_date = f"{date_match.group(1)} {remove_ordinal_indicator_from_date_string(date_match.group(2))} {date_match.group(3)}"
                collection_date = datetime.strptime(collection_date, "%A %d %B")

                if (datetime.now().month == 12) and (collection_date.month == 1):
                    collection_date = collection_date.replace(year=next_year)
                else:
                    collection_date = collection_date.replace(year=current_year)

                # Get bin types
                bins = collection.find_all("div", class_="field__item")
                for bin_type in bins:
                    dict_data = {
                        "type": bin_type.text.strip(),
                        "collectionDate": collection_date.strftime(date_format),
                    }
                    bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
