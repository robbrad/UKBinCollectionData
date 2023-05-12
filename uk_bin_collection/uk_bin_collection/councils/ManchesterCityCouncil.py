from datetime import datetime

import requests
from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # Get and check UPRN
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        # Start a new session to walk through the form
        s = requests.session()

        # There's a cookie that makes the whole thing valid when you search for a postcode,
        # but postcode and UPRN is a hassle imo, so this makes a request for the session to get a cookie
        # using a Manchester City Council postcode I hardcoded in the data payload
        postcode_request_header = {
            "authority": "www.manchester.gov.uk",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
            "image/webp,image/apng,*/*;q=0.8",
            "accept-language": "en-GB,en;q=0.6",
            "cache-control": "max-age=0",
            # Requests sorts cookies= alphabetically
            "origin": "https://www.manchester.gov.uk",
            "referer": "https://www.manchester.gov.uk/bincollections",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "sec-gpc": "1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, "
            "like Gecko) Chrome/104.0.5112.102 Safari/537.36",
        }
        postcode_request_data = {
            "mcc_bin_dates_search_term": "M2 5DB",
            "mcc_bin_dates_submit": "Go",
        }
        response = s.post(
            "https://www.manchester.gov.uk/bincollections",
            headers=postcode_request_header,
            data=postcode_request_data,
        )

        # Make a POST with the same cookie-fied session using the user's UPRN data
        uprn_request_headers = {
            "authority": "www.manchester.gov.uk",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "accept-language": "en-GB,en;q=0.6",
            "cache-control": "max-age=0",
            # Requests sorts cookies= alphabetically
            # 'cookie': 'TestCookie=Test; CookieConsent={stamp:%27D8rypjMDBJhpfMWybSMdGXP1hCZWGJYtGETiMTu1UuXTdRIKl8SU5g==%27%2Cnecessary:true%2Cpreferences:true%2Cstatistics:true%2Cmarketing:true%2Cver:6%2Cutc:1661783732090%2Cregion:%27gb%27}; PHPSESSID=kElJxYAt%2Cf-4ZWoskt0s5tn32BUQRXDYUVp3G-NsqOAOaeIcKlm2T4r7ATSgqfz6',
            "origin": "https://www.manchester.gov.uk",
            "referer": "https://www.manchester.gov.uk/bincollections",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "sec-gpc": "1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36",
        }
        uprn_request_data = {
            "mcc_bin_dates_uprn": user_uprn,
            "mcc_bin_dates_submit": "Go",
        }
        response = s.post(
            "https://www.manchester.gov.uk/bincollections",
            headers=uprn_request_headers,
            data=uprn_request_data,
        )

        # Make that BS4 object and use it to prettify the response
        soup = BeautifulSoup(response.content, features="html.parser")
        soup.prettify()

        # Get the collection items on the page and strip the bits of text that we don't care for
        collections = []
        for bin in soup.find_all("div", {"class": "collection"}):
            bin_type = bin.find_next("h3").text.replace("  DUE TODAY", "").strip()
            next_collection = bin.find_next("p").text.replace("Next collection ", "")
            next_collection = datetime.strptime(next_collection, "%A %d %b %Y")
            collections.append((bin_type, next_collection))

        # Sort the collections by date order rather than bin type, then return as a dictionary (with str date)
        ordered_data = sorted(collections, key=lambda x: x[1])
        data = {"bins": []}
        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
