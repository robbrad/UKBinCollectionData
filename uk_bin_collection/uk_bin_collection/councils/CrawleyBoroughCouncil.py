#!/usr/bin/env python3

from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
from datetime import datetime
from common import *

import requests

# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """


    def parse_data(self, page: str, **kwargs) -> dict:
        # Make a BS4 object
        requests.packages.urllib3.disable_warnings()
        uprn = kwargs.get("uprn")
        try:
            if uprn is None or uprn == "":
                raise ValueError("Invalid UPRN")
        except Exception as ex:
            print(f"Exception encountered: {ex}")
            print(
                "Please check the provided UPRN. If this error continues, please first trying setting the "
                "UPRN manually on line 115 before raising an issue."
            )

        usrn = get_usrn(uprn)
        day = datetime.now().date().strftime("%d")
        month = datetime.now().date().strftime("%m")
        year = datetime.now().date().strftime("%Y")

        api_url = (
            f"https://my.crawley.gov.uk/appshost/firmstep/self/apps/custompage/waste?language=en&uprn={uprn}"
            f"&usrn={usrn}&day={day}&month={month}&year={year}"
        )
        response = requests.get(api_url)

        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        titles = [title.text for title in soup.select(".title")]
        collection_tag = soup.body.find_all(
            "div", {"class": "col-md-6 col-sm-6 col-xs-6"}, text="Next collection"
        )
        bin_index = 0
        for tag in collection_tag:
            for item in tag.next_elements:
                if str(item).startswith('<div class="date text-right text-grey">'):
                    collection_date = datetime.strptime(item.text, "%A %d %B").strftime(
                        "%d/%m"
                    )
                    dict_data = {
                        "type": titles[bin_index].strip(),
                        "collectionDate": collection_date,
                    }
                    data["bins"].append(dict_data)
                    bin_index += 1
                    break
        return data
