from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

import requests

# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # Get postcode and UPRN from kwargs
        user_postcode = kwargs.get('postcode')
        user_uprn = kwargs.get('uprn')
        check_postcode(user_postcode)
        check_uprn(user_uprn)

        # Build URL to parse
        council_url = f"https://swale.gov.uk/bins-littering-and-the-environment/bins/collection-days?postcode={user_postcode.replace(' ', '+')}&addresses={user_uprn}&address-submit="

        # Parse URL and read if connection successful
        response = requests.get(council_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, features="html.parser")
            soup.prettify()
        else:
            raise ConnectionAbortedError("Could not parse council website.")

        data = {"bins": []}

        # Get the collection bullet points on the page and parse them
        form_area = soup.find("form", {"class": "integration bin-lookup"})
        collections = [item.text.strip().split(",") for item in form_area.find_all("li")]
        for c in collections:
            bin_type = c[0].strip()
            # temp_date = c[2].strip() + " " + str(datetime.now().year)
            bin_date = datetime.strptime(c[2].strip() + " " + str(datetime.now().year), "%d %B %Y").strftime(date_format)
            dict_data = {
                "type":           bin_type,
                "collectionDate": bin_date
            }
            data["bins"].append(dict_data)

        return data
