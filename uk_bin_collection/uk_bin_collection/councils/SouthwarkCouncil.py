from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def extract_collection_date(section, section_id):
    """
    Helper function to safely extract title and collection date from a section.
    Returns tuple (title, collection_date) or (None, None) if not found.
    """
    if not section:
        return None, None

    title_element = section.find("p", {"id": section_id})
    if not title_element:
        return None, None

    title = title_element.text

    next_collection_text = section.find(
        string=lambda text: text and "Next collection" in text
    )

    if not next_collection_text:
        return title, None

    try:
        collection_date = str(next_collection_text).strip().split(": ")[1]
        return title, collection_date
    except (IndexError, AttributeError):
        return title, None


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
        data = {"bins": []}

        baseurl = "https://services.southwark.gov.uk/bins/lookup/"
        url = baseurl + user_uprn

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
        }

        # Make the web request
        response = requests.get(url, headers=headers).text

        soup = BeautifulSoup(response, "html.parser")

        # Extract recycling collection information
        recycling_section = soup.find(
            "div", {"aria-labelledby": "recyclingCollectionTitle"}
        )
        if recycling_section:
            recycling_title, recycling_next_collection = extract_collection_date(
                recycling_section, "recyclingCollectionTitle"
            )
            if recycling_title and recycling_next_collection:
                dict_data = {
                    "type": recycling_title,
                    "collectionDate": datetime.strptime(
                        recycling_next_collection, "%a, %d %B %Y"
                    ).strftime("%d/%m/%Y"),
                }
                data["bins"].append(dict_data)

        # Extract refuse collection information
        refuse_section = soup.find("div", {"aria-labelledby": "refuseCollectionTitle"})
        if refuse_section:
            refuse_title, refuse_next_collection = extract_collection_date(
                refuse_section, "refuseCollectionTitle"
            )
            if refuse_title and refuse_next_collection:
                dict_data = {
                    "type": refuse_title,
                    "collectionDate": datetime.strptime(
                        refuse_next_collection, "%a, %d %B %Y"
                    ).strftime("%d/%m/%Y"),
                }
                data["bins"].append(dict_data)

        # Extract food waste collection information
        food_section = soup.find(
            "div", {"aria-labelledby": "domesticFoodCollectionTitle"}
        )
        if food_section:
            food_title, food_next_collection = extract_collection_date(
                food_section, "domesticFoodCollectionTitle"
            )
            if food_title and food_next_collection:
                dict_data = {
                    "type": food_title,
                    "collectionDate": datetime.strptime(
                        food_next_collection, "%a, %d %B %Y"
                    ).strftime("%d/%m/%Y"),
                }
                data["bins"].append(dict_data)

        # Extract communal food waste collection information
        comfood_section = soup.find(
            "div", {"aria-labelledby": "communalFoodCollectionTitle"}
        )
        if comfood_section:
            comfood_title, comfood_next_collection = extract_collection_date(
                comfood_section, "communalFoodCollectionTitle"
            )
            if comfood_title and comfood_next_collection:
                dict_data = {
                    "type": comfood_title,
                    "collectionDate": datetime.strptime(
                        comfood_next_collection, "%a, %d %B %Y"
                    ).strftime("%d/%m/%Y"),
                }
                data["bins"].append(dict_data)

        comrec_section = soup.find(
            "div", {"aria-labelledby": "recyclingCommunalCollectionTitle"}
        )
        if comrec_section:
            comrec_title, comrec_next_collection = extract_collection_date(
                comrec_section, "recyclingCommunalCollectionTitle"
            )
            if comrec_title and comrec_next_collection:
                dict_data = {
                    "type": comrec_title,
                    "collectionDate": datetime.strptime(
                        comrec_next_collection, "%a, %d %B %Y"
                    ).strftime("%d/%m/%Y"),
                }
                data["bins"].append(dict_data)

        comref_section = soup.find(
            "div", {"aria-labelledby": "refuseCommunalCollectionTitle"}
        )
        if comref_section:
            comref_title, comref_next_collection = extract_collection_date(
                comref_section, "refuseCommunalCollectionTitle"
            )
            if comref_title and comref_next_collection:
                dict_data = {
                    "type": comref_title,
                    "collectionDate": datetime.strptime(
                        comref_next_collection, "%a, %d %B %Y"
                    ).strftime("%d/%m/%Y"),
                }
                data["bins"].append(dict_data)

        return data
