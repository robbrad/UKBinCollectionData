from bs4 import BeautifulSoup
from datetime import datetime
import requests
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass

COLLECTION_KINDS = {
    "waste": "rteelem_ctl03_pnlCollections_Refuse",
    "recycling": "rteelem_ctl03_pnlCollections_Recycling",
    "glass": "rteelem_ctl03_pnlCollections_Glass"
}

class CouncilClass(AbstractGetBinDataClass):

    def get_data(self, address_url):
        # Unused, we need the uprn!
        return None

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        request_headers = {
            "cookie": f"WhenAreMyBinsCollected={user_uprn}"
        }
        response = requests.get(
            "https://www.basingstoke.gov.uk/bincollections",
            headers=request_headers,
        )

        if response.status_code != 200:
            raise SystemError("Error retrieving data! Please try again or raise an issue on GitHub!")


        # Make a BS4 object
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        print(response.text)

        bins = []

        for collection_type, collection_class in COLLECTION_KINDS.items():
            for date in soup.select(f"div#{collection_class} li"):
                bins.append({
                    "type": collection_type,
                    "collectionDate": datetime.strptime(
                        # Friday, 21 July 2023
                        date.get_text(strip=True),
                        '%A, %d %B %Y'
                    ).strftime('%d/%m/%Y')
                })

        return {
            "bins": bins
        }
