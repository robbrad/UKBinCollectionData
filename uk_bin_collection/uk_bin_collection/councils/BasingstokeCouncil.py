from bs4 import BeautifulSoup
from datetime import datetime
import requests
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass

COLLECTION_KINDS = {
    "waste": "rteelem_ctl03_pnlCollections_Refuse",
    "recycling": "rteelem_ctl03_pnlCollections_Recycling",
    "glass": "rteelem_ctl03_pnlCollections_Glass",
    # Garden waste data is only returned if the property is subscribed to the Garden Waste service
    "garden": "rteelem_ctl03_pnlCollections_GardenWaste"
}


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        requests.packages.urllib3.disable_warnings()

        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        cookies = {
            'cookie_control_popup': 'A',
            'WhenAreMyBinsCollected': f'{user_uprn}',
        }

        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Referer': 'https://www.basingstoke.gov.uk/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-User': '?1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.188 Safari/537.36',
        }

        response = requests.get('https://www.basingstoke.gov.uk/bincollections', cookies=cookies,
                                 headers=headers, verify=False)

        if response.status_code != 200 or response.text == '0|error|500||':
            raise SystemError("Error retrieving data! Please try again or raise an issue on GitHub!")



        # Make a BS4 object
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        bins = []

        for collection_type, collection_class in COLLECTION_KINDS.items():
            for date in soup.select(f"div#{collection_class} li"):
                bins.append({
                    "type": collection_type,
                    "collectionDate": datetime.strptime(
                        # Friday, 21 July 2023
                        date.get_text(strip=True),
                        '%A, %d %B %Y'
                    ).strftime(date_format)
                })

        return {
            "bins": bins
        }
