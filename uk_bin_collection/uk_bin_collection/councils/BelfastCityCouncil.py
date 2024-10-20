import logging
from datetime import datetime

import requests
import urllib

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

    def get_session_variable(self, soup, id) -> str:
        """Extract ASP.NET variable from the HTML."""
        element = soup.find("input", {"id": id})
        if element:
            return element.get("value")
        else:
            raise ValueError(f"Unable to find element with id: {id}")

    def parse_data(self, page: str, **kwargs) -> dict:
        bin_data = {"bins": []}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/119.0"
        }

        session = requests.Session()
        session.headers.update(headers)

        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        URL = "https://online.belfastcity.gov.uk/find-bin-collection-day/Default.aspx"

        # Build initial ASP.NET variables for Postcode Find address
        response = session.get(URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        form_data = {
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": self.get_session_variable(soup, "__VIEWSTATE"),
            "__VIEWSTATEGENERATOR": self.get_session_variable(
                soup, "__VIEWSTATEGENERATOR"
            ),
            "__SCROLLPOSITIONX": "0",
            "__SCROLLPOSITIONY": "0",
            "__EVENTVALIDATION": self.get_session_variable(soup, "__EVENTVALIDATION"),
            "ctl00$MainContent$searchBy_radio": "P",
            "ctl00$MainContent$Street_textbox": "",
            "ctl00$MainContent$Postcode_textbox": user_postcode,
            "ctl00$MainContent$AddressLookup_button": "Find address",
        }

        # Build intermediate ASP.NET variables for uprn Select address
        response = session.post(URL, data=form_data)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        form_data = {
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": self.get_session_variable(soup, "__VIEWSTATE"),
            "__VIEWSTATEGENERATOR": self.get_session_variable(
                soup, "__VIEWSTATEGENERATOR"
            ),
            "__SCROLLPOSITIONX": "0",
            "__SCROLLPOSITIONY": "0",
            "__EVENTVALIDATION": self.get_session_variable(soup, "__EVENTVALIDATION"),
            "ctl00$MainContent$searchBy_radio": "P",
            "ctl00$MainContent$Street_textbox": "",
            "ctl00$MainContent$Postcode_textbox": user_postcode,
            "ctl00$MainContent$lstAddresses": user_uprn,
            "ctl00$MainContent$SelectAddress_button": "Select address",
        }

        # Actual http call to get Bins Data
        response = session.post(URL, data=form_data)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Find Bins table and data
        table = soup.find("div", {"id": "binsGrid"})
        if table:
            rows = table.find_all("tr")
            for row in rows:
                columns = row.find_all("td")
                if len(columns) >= 4:
                    collection_type = columns[0].get_text(strip=True)
                    collection_date_raw = columns[3].get_text(strip=True)
                    # if the month number is a single digit there are 2 spaces, stripping all spaces to make it consistent
                    collection_date = datetime.strptime(
                        collection_date_raw.replace(" ", ""), "%a%b%d%Y"
                    )
                    bin_entry = {
                        "type": collection_type,
                        "collectionDate": collection_date.strftime(date_format),
                    }
                    bin_data["bins"].append(bin_entry)
        return bin_data
