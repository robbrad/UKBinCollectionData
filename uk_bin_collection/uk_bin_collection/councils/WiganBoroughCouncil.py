from datetime import datetime

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
        # Get and check UPRN
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        user_uprn = user_uprn.zfill(
            12
        )  # Wigan is expecting 12 character UPRN or else it falls over, expects 0 padded UPRNS at the start for any that aren't 12 chars

        user_postcode = kwargs.get("postcode")
        check_postcode(user_postcode)

        # Start a new session to walk through the form
        requests.packages.urllib3.disable_warnings()
        s = requests.session()

        # Get our initial session running
        response = s.get("https://apps.wigan.gov.uk/MyNeighbourhood/")

        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        # Grab the ASP variables needed to continue
        payload = {
            "__VIEWSTATE": (soup.find("input", {"id": "__VIEWSTATE"}).get("value")),
            "__VIEWSTATEGENERATOR": (
                soup.find("input", {"id": "__VIEWSTATEGENERATOR"}).get("value")
            ),
            "__EVENTVALIDATION": (
                soup.find("input", {"id": "__EVENTVALIDATION"}).get("value")
            ),
            "ctl00$ContentPlaceHolder1$txtPostcode": (user_postcode),
            "ctl00$ContentPlaceHolder1$btnPostcodeSearch": ("Search"),
        }

        # Use the above to get to the next page with address selection
        response = s.post("https://apps.wigan.gov.uk/MyNeighbourhood/", payload)

        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        # Load the new variables that are constant and can't be gotten from the page
        payload = {
            "__EVENTTARGET": ("ctl00$ContentPlaceHolder1$lstAddresses"),
            "__EVENTARGUMENT": (""),
            "__LASTFOCUS": (""),
            "__VIEWSTATE": (soup.find("input", {"id": "__VIEWSTATE"}).get("value")),
            "__VIEWSTATEGENERATOR": (
                soup.find("input", {"id": "__VIEWSTATEGENERATOR"}).get("value")
            ),
            "__EVENTVALIDATION": (
                soup.find("input", {"id": "__EVENTVALIDATION"}).get("value")
            ),
            "ctl00$ContentPlaceHolder1$txtPostcode": (user_postcode),
            "ctl00$ContentPlaceHolder1$lstAddresses": ("UPRN" + user_uprn),
        }

        # Get the final page with the actual dates
        response = s.post("https://apps.wigan.gov.uk/MyNeighbourhood/", payload)

        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        # Get the dates.
        for bins in soup.find_all("div", {"class": "BinsRecycling"}):
            bin_type = bins.find("h2").text
            binCollection = bins.find("div", {"class": "dateWrapper-next"}).get_text(
                strip=True
            )
            binData = datetime.strptime(
                re.sub(r"(\d)(st|nd|rd|th)", r"\1", binCollection), "%A%d%b%Y"
            )
            if binData:
                dict_data = {
                    "type": bin_type,
                    "collectionDate": binData.strftime(date_format),
                }
                data["bins"].append(dict_data)

        return data
