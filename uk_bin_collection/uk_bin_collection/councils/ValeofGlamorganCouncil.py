import json

from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

import requests
import json


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

        headers = {
            'Accept':             '*/*',
            'Accept-Language':    'en-GB,en;q=0.6',
            'Connection':         'keep-alive',
            'Referer':            'https://www.valeofglamorgan.gov.uk/',
            'Sec-Fetch-Dest':     'script',
            'Sec-Fetch-Mode':     'no-cors',
            'Sec-Fetch-Site':     'same-site',
            'Sec-GPC':            '1',
            'sec-ch-ua':          '"Not?A_Brand";v="8", "Chromium";v="108", "Brave";v="108"',
            'sec-ch-ua-mobile':   '?0',
            'sec-ch-ua-platform': '"Windows"',
        }

        params = {
            'RequestType': 'LocalInfo',
            'ms':          'ValeOfGlamorgan/AllMaps',
            'group':       'Community and Living|Refuse HIDE2',
            'type':        'json',
            'callback':    'AddressInfoCallback',
            'uid':         user_uprn,
            'import':      'jQuery35108514154283927682_1673022974838',
            '_':           '1673022974840',
        }

        response = requests.get('https://myvale.valeofglamorgan.gov.uk/getdata.aspx', params=params,
                                headers=headers).text
        bin_week = str(json.loads(response)["Results"]["Refuse_HIDE2"]["Your_Refuse_round_is"]).replace(" ", "-")
        schedule_url = f"https://www.valeofglamorgan.gov.uk/en/living/Recycling-and-Waste/collections/{bin_week}.aspx"
        response = requests.get(schedule_url, verify=False)

        # Make a BS4 object
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        table = soup.find("table", {"class": "TableStyle_Activities"}).find("tbody")
        table_headers = table.find("tr").find_all("th")
        table_rows = table.select("td")


        for bins in soup.select('div[class*="service-item"]'):
            bin_type = bins.div.h3.text.strip()
            binCollection = bins.select("div > p")[1].get_text(strip=True)
            # binImage = "https://myaccount.stockport.gov.uk"   bins.img['src']
            if binCollection:
                data[bin_type] = binCollection

        return data
