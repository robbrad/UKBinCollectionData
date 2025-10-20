from datetime import datetime

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import check_uprn
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

    title = title_element.get_text(strip=True)

    next_collection_text = section.find(
        string=lambda t: isinstance(t, str) and "next collection" in t.lower()
    )

    if not next_collection_text:
        return title, None

    text = str(next_collection_text).strip()
    _, sep, rhs = text.partition(":")
    if not sep:
        return title, None
    collection_date = rhs.strip()
    return title, collection_date


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

        # Make the web request using the common helper (standard UA, timeout, logging)
        response = self.get_data(url).text

        soup = BeautifulSoup(response, "html.parser")
        # Extract collection information for all bin types
        section_ids = (
            "recyclingCollectionTitle",
            "refuseCollectionTitle",
            "domesticFoodCollectionTitle",
            "communalFoodCollectionTitle",
            "recyclingCommunalCollectionTitle",
            "refuseCommunalCollectionTitle",
        )

        for section_id in section_ids:
            section = soup.find("div", {"aria-labelledby": section_id})
            if not section:
                continue

            title, next_collection = extract_collection_date(section, section_id)
            if not (title and next_collection):
                continue

            try:
                parsed = datetime.strptime(next_collection, "%a, %d %B %Y")
            except ValueError:
                continue

            data["bins"].append(
                {
                    "type": title,
                    "collectionDate": parsed.strftime("%d/%m/%Y"),
                }
            )

        return data
