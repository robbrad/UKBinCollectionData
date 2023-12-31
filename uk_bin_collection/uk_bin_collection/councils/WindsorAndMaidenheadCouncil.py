from datetime import datetime
from urllib.parse import urlparse

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
        root_url = "https://my.rbwm.gov.uk"
        href_url = ""
        api_url = "https://my.rbwm.gov.uk/block_refresh/block/47/node/136968?"
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")

        data = {"bins": []}

        requests.packages.urllib3.disable_warnings()
        s = requests.session()
        # Form start
        headers = {
            "authority": "my.rbwm.gov.uk",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "accept-language": "en-GB,en;q=0.8",
            "cache-control": "max-age=0",
            "referer": "https://my.rbwm.gov.uk/special/your-collection-dates?uprn=100080371082&subdate=2022-08-19&addr=11%20Douglas%20Lane%20Wraysbury%20Staines%20TW19%205NF",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "sec-gpc": "1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36",
        }
        s.get(
            "https://my.rbwm.gov.uk/special/find-your-collection-dates", headers=headers
        )

        # Select address
        headers = {
            "authority": "my.rbwm.gov.uk",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "accept-language": "en-GB,en;q=0.8",
            "cache-control": "max-age=0",
            "origin": "https://my.rbwm.gov.uk",
            "referer": "https://my.rbwm.gov.uk/special/find-your-collection-dates",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "sec-gpc": "1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36",
        }
        request_data = {
            "atTxtStreet": user_postcode,
            "nodeid": "x",
            "formname": "x",
            "pg": "20",
            "start": "1",
            "selectaddress": "Select this address",
            "selectheading": "The following addresses match the address you entered - choose your address",
            "arg": "",
        }
        response = s.post(
            "https://my.rbwm.gov.uk/special/address-selector-collection-dates",
            headers=headers,
            data=request_data,
        )

        soup = BeautifulSoup(response.content, features="html.parser")
        soup.prettify()

        table = soup.find("table")
        if table:
            table_rows = table.find_all("tr")
            for tr in table_rows:
                td = tr.find_all("td")
                # row = [i.text for i in td]
                for item in td:
                    if user_paon in item.text and user_postcode in item.text:
                        href_url = td[1].find("a").get("href")
                        continue

            # Getting to bin data
            headers = {
                "authority": "my.rbwm.gov.uk",
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "accept-language": "en-GB,en;q=0.8",
                "referer": "https://my.rbwm.gov.uk/special/address-selector-collection-dates",
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-fetch-user": "?1",
                "sec-gpc": "1",
                "upgrade-insecure-requests": "1",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36",
            }
            params = {}
            parsed_params = urlparse(href_url).query.split("&")
            for item in parsed_params:
                values = item.split("=")
                params.update({values[0]: values[1]})

            s.get(root_url + href_url, params=params, headers=headers)
            response = s.get(
                api_url + href_url.split("?")[1], params=params, headers=headers
            )

            soup = BeautifulSoup(response.content, features="html.parser")
            soup.prettify()

            table_rows = soup.find_all("tr")
            for tr in table_rows:
                td = tr.find_all("td")
                row = [i.text for i in td]

                if len(row) > 0:
                    dict_data = {
                        "type": row[0],
                        "collectionDate": row[1],
                    }
                    data["bins"].append(dict_data)

        return data
