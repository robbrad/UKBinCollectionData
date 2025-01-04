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

        URI = (
            f"https://maps.monmouthshire.gov.uk/?action=SetAddress&UniqueId={user_uprn}"
        )

        # Make the GET request
        response = requests.get(URI)

        # Parse the HTML
        soup = BeautifulSoup(response.content, "html.parser")

        waste_collections_div = soup.find("div", {"aria-label": "Waste Collections"})

        # Find all bin collection panels
        bin_panels = waste_collections_div.find_all("div", class_="atPanelContent")

        current_year = datetime.now().year
        current_month = datetime.now().month

        for panel in bin_panels:
            # Extract bin name (e.g., "Household rubbish bag")
            bin_name = panel.find("h4").text.strip().replace("\r", "").replace("\n", "")

            # Extract collection date (e.g., "Monday 9th December")
            date_tag = panel.find("p")
            if date_tag and "Your next collection date is" in date_tag.text.strip().replace("\r", "").replace("\n", ""):
                collection_date = date_tag.find("strong").text.strip()
            else:
                continue

            collection_date = datetime.strptime(
                remove_ordinal_indicator_from_date_string(collection_date), "%A %d %B"
            )

            if (current_month > 9) and (collection_date.month < 4):
                collection_date = collection_date.replace(year=(current_year + 1))
            else:
                collection_date = collection_date.replace(year=current_year)

            dict_data = {
                "type": bin_name,
                "collectionDate": collection_date.strftime("%d/%m/%Y"),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
