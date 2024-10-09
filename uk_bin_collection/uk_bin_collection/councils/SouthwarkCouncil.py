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
        data = {"bins": []}

        baseurl = "https://www.southwark.gov.uk/bins/lookup/"
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
            recycling_title = recycling_section.find(
                "p", {"id": "recyclingCollectionTitle"}
            ).text
            recycling_next_collection = (
                recycling_section.find(text=lambda text: "Next collection" in text)
                .strip()
                .split(": ")[1]
            )

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
            refuse_title = refuse_section.find(
                "p", {"id": "refuseCollectionTitle"}
            ).text
            refuse_next_collection = (
                refuse_section.find(text=lambda text: "Next collection" in text)
                .strip()
                .split(": ")[1]
            )

            dict_data = {
                "type": refuse_title,
                "collectionDate": datetime.strptime(
                    refuse_next_collection, "%a, %d %B %Y"
                ).strftime("%d/%m/%Y"),
            }
            data["bins"].append(dict_data)

        # Extract food waste collection information
        food_section = soup.find("div", {"aria-labelledby": "organicsCollectionTitle"})
        if food_section:
            food_title = food_section.find("p", {"id": "organicsCollectionTitle"}).text
            food_next_collection = (
                food_section.find(text=lambda text: "Next collection" in text)
                .strip()
                .split(": ")[1]
            )

            dict_data = {
                "type": food_title,
                "collectionDate": datetime.strptime(
                    food_next_collection, "%a, %d %B %Y"
                ).strftime("%d/%m/%Y"),
            }
            data["bins"].append(dict_data)

        comrec_section = soup.find(
            "div", {"aria-labelledby": "recyclingCommunalCollectionTitle"}
        )
        if comrec_section:
            comrec_title = comrec_section.find(
                "p", {"id": "recyclingCommunalCollectionTitle"}
            ).text
            comrec_next_collection = (
                comrec_section.find(text=lambda text: "Next collection" in text)
                .strip()
                .split(": ")[1]
            )

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
            comref_title = comref_section.find(
                "p", {"id": "refuseCommunalCollectionTitle"}
            ).text
            comref_next_collection = (
                comref_section.find(text=lambda text: "Next collection" in text)
                .strip()
                .split(": ")[1]
            )

            dict_data = {
                "type": comref_title,
                "collectionDate": datetime.strptime(
                    comref_next_collection, "%a, %d %B %Y"
                ).strftime("%d/%m/%Y"),
            }
            data["bins"].append(dict_data)

        return data
