import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        check_uprn(user_uprn)
        check_postcode(user_postcode)
        bindata = {"bins": []}

        user_postcode = user_postcode.replace(" ", "+")

        API_URL = (
            f"https://your.westlancs.gov.uk/yourwestlancs.aspx?address={user_postcode}"
        )

        session = requests.Session()
        response = session.get(API_URL)
        soup = BeautifulSoup(response.content, "html.parser")

        soup = BeautifulSoup(response.content, features="html.parser")
        soup.prettify()

        pattern = r"SELECT\$\d+"

        # Loop through each row to find the one with the target UPRN
        for row in soup.find("table", class_="striped-table").find_all("tr"):
            cells = row.find_all("td")
            if len(cells) > 2 and cells[2].get_text(strip=True) == user_uprn:
                link = row.find("a", href=True)
                if link:
                    match = re.search(pattern, link["href"])

                    # Extract important form data like __VIEWSTATE and __EVENTVALIDATION
                    viewstate = soup.find("input", {"name": "__VIEWSTATE"})["value"]
                    eventvalidation = soup.find("input", {"name": "__EVENTVALIDATION"})[
                        "value"
                    ]

                    # Parameters for the "click" - usually __EVENTTARGET and __EVENTARGUMENT
                    post_data = {
                        "__VIEWSTATE": viewstate,
                        "__EVENTVALIDATION": eventvalidation,
                        "__EVENTTARGET": "ctl00$MainContent$GridView1",
                        "__EVENTARGUMENT": match.group(
                            0
                        ),  # Modify as needed for the specific link
                    }

                    post_response = session.post(API_URL, data=post_data)

                    soup = BeautifulSoup(post_response.text, features="html.parser")
                    StreetSceneTable = soup.find("table", {"id": "StreetSceneTable"})

                    if StreetSceneTable:

                        # Extract each collection date or information by locating the span elements
                        refuse_collection = soup.find(
                            "span", id="ctl00_MainContent_lbNextDomRoundZones"
                        ).text.strip()
                        recycling_collection = soup.find(
                            "span", id="ctl00_MainContent_lbNextRecRoundZones"
                        ).text.strip()
                        garden_waste_collection = soup.find(
                            "span", id="ctl00_MainContent_lbNextGardenRoundZones"
                        ).text.strip()

                        # Structure the extracted data in a dictionary
                        bin_schedule = [
                            {
                                "Service": "Refuse Collection",
                                "Date": refuse_collection,
                            },
                            {
                                "Service": "Recycling Collection",
                                "Date": recycling_collection,
                            },
                            {
                                "Service": "Garden Waste Collection",
                                "Date": garden_waste_collection,
                            },
                        ]

                        if bin_schedule:
                            for service in bin_schedule:
                                if service["Date"] != "Not subscribed":
                                    dict_data = {
                                        "type": service["Service"],
                                        "collectionDate": service["Date"],
                                    }
                                    bindata["bins"].append(dict_data)

                else:
                    print("No link found in the row with the target UPRN.")
                    break

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )
        return bindata
