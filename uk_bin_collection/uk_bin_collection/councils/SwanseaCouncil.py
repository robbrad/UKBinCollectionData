import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

HEADERS = {
    "user-agent": "Mozilla/5.0",
}


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete class implementing all abstract operations of the base class.
    """

    def get_session_variable(self, soup, id) -> str:
        """Extract ASP.NET variable from the HTML."""
        element = soup.find("input", {"id": id})
        if element:
            return element.get("value")
        else:
            raise ValueError(f"Unable to find element with id: {id}")

    def parse_data(self, page: str, **kwargs) -> dict:
        # Create a session to handle cookies and headers
        session = requests.Session()
        session.headers.update(HEADERS)
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        URL = "https://www1.swansea.gov.uk/recyclingsearch/"

        # Get initial ASP.NET variables
        response = session.get(URL)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        data = {
            "__VIEWSTATE": self.get_session_variable(soup, "__VIEWSTATE"),
            "__VIEWSTATEGENERATOR": self.get_session_variable(
                soup, "__VIEWSTATEGENERATOR"
            ),
            "__VIEWSTATEENCRYPTED": "",
            "__EVENTVALIDATION": self.get_session_variable(soup, "__EVENTVALIDATION"),
            "txtRoadName": user_uprn,
            "txtPostCode": user_postcode,
            "btnSearch": "Search",
        }

        # Get the collection calendar
        response = session.post(URL, data=data)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        next_refuse_date = soup.find("span", {"id": "lblNextRefuse"}).text.strip()
        next_recycling_date = soup.find("span", {"id": "lblNextRecycling"}).text.strip()

        bin_data = {
            "bins": [
                {"type": "Pink Week", "collectionDate": next_refuse_date},
                {"type": "Green Week", "collectionDate": next_recycling_date},
            ]
        }

        return bin_data
