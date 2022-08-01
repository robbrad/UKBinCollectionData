from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

import re
import requests
import json
from datetime import datetime


def parse_header(raw_header: str) -> dict:
    """
    Parses a header string and returns one that can be useful
        :param raw_header: header as a string, with values to separate as pipe (|)
        :return: header in a dictionary format that can be used in requests
    """
    header = dict()
    for line in raw_header.split("|"):

        if line.startswith(":"):
            a, b = line[1:].split(":", 1)
            a = f":{a}"
        else:
            a, b = line.split(":", 1)

        header[a.strip()] = b.strip()

    return header


def get_address_uprn(postcode: str, paon: str, api_url: str) -> str:
    """
Gets the UPRN and address in desired format
    :param postcode: Postcode to use
    :param paon: House number to use
    :param api_url: API to POST
    :return: UPRN and postcode in str format
    """
    addr = ""
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id":      "1642260173663",
        "method":  "ictGetAddressList",
        "params":  {
            "postcode":  f"{postcode.replace(' ', '')}",
            "localonly": "true"
        }
    })
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(api_url, data=payload, headers=headers)

    json_response = json.loads(response.content)
    results = json_response['result']
    result_line = ""

    for item in results:
        while len(result_line) < 1:
            result_line = [element for element in item.get("Address").split()
                           if item.get("Address").split()[0] == paon.strip()]
            addr = item.get("UPRN") + "|" + item.get("Address")
            break

    return addr


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        api_url = "https://www.southtyneside.gov.uk/apiserver/ajaxlibrary/"
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        postcode_re = "^([A-Za-z][A-Ha-hJ-Yj-y]?[0-9][A-Za-z0-9]? ?[0-9][A-Za-z]{2}|[Gg][Ii][Rr] ?0[Aa]{2})$"

        try:
            if user_postcode is None or not re.fullmatch(postcode_re, user_postcode):
                raise ValueError("Invalid postcode")
        except Exception as ex:
            print(f"Exception encountered: {ex}")
            print(
                "Please check the provided postcode. If this error continues, please first trying setting the "
                "postcode manually on line 24 before raising an issue."
            )
            exit(1)

        try:
            if user_paon is None:
                raise ValueError("Invalid house number")
        except Exception as ex:
            print(f"Exception encountered: {ex}")
            print(
                "Please check the provided house number. If this error continues, please first trying setting the "
                "house number manually on line 25 before raising an issue."
            )
            exit(1)

        uprn = get_address_uprn(user_postcode, user_paon, api_url)

        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        for bins in soup.select('div[class*="service-item"]'):
            bin_type = bins.div.h3.text.strip()
            binCollection = bins.select("div > p")[1].get_text(strip=True)
            # binImage = "https://myaccount.stockport.gov.uk"   bins.img['src']
            if binCollection:
                data[bin_type] = binCollection

        return data
