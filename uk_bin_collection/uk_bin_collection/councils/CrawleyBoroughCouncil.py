#!/usr/bin/env python3

from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
from dotenv import load_dotenv
from datetime import datetime

import requests
import os
import json


def get_usrn(uprn: str) -> str:
    """
Gets a USRN (street reference) using the Ordinance Survey's Linked Identifiers API. Requires an API key available
from OS Data Hub (free). Can either remove lines 5 and 21 and include your own, or place it in a .env file.
    :param uprn: The property's UPRN reference
    :return: USRN as string
    """
    load_dotenv()
    api_key = os.getenv("OS_API_KEY")  # put yours here (and remove `from dotenv import load_dotenv` on line 5)
    api_url = f"https://api.os.uk/search/links/v1/featureTypes/BLPU/{uprn}?key={api_key}"
    json_response = json.loads(requests.get(api_url).content)
    street_data = [item.get("correlatedIdentifiers") if item.get("correlatedFeatureType") == "Street" else None
                   for item in json_response["correlations"]]
    try:
        street_usrn = [line.get("identifier") for item in street_data if item is not None for line in item][0]
    except Exception as ex:
        raise ValueError("USRN not found! Please check API key or UPRN.")
        exit(1)
    return street_usrn


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # Make a BS4 object
        uprn = kwargs.get("uprn")
        try:
            if uprn is None or uprn == "":
                raise ValueError("Invalid UPRN")
        except Exception as ex:
            print(f"Exception encountered: {ex}")
            print("Please check the provided UPRN. If this error continues, please first trying setting the "
                  "UPRN manually on line 115 before raising an issue.")

        usrn = get_usrn(uprn)
        day = datetime.now().date().strftime("%d")
        month = datetime.now().date().strftime("%m")
        year = datetime.now().date().strftime("%Y")

        api_url = f"https://my.crawley.gov.uk/appshost/firmstep/self/apps/custompage/waste?language=en&uprn={uprn}" \
                  f"&usrn={usrn}&day={day}&month={month}&year={year}"
        response = requests.get(api_url)

        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        titles = [title.text for title in soup.select(".title")]
        collection_tag = soup.body.find_all("div", {"class": "col-md-6 col-sm-6 col-xs-6"}, text="Next collection")
        bin_index = 0
        for tag in collection_tag:
            for item in tag.next_elements:
                if str(item).startswith('<div class="date text-right text-grey">'):
                    collection_date = datetime.strptime(item.text, "%A %d %B").strftime("%d/%m")
                    dict_data = {
                        "type":           titles[bin_index].strip(),
                        "collectionDate": collection_date,
                    }
                    data["bins"].append(dict_data)
                    bin_index += 1
                    break
        return data
