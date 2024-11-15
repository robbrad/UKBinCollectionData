from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


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
        bindata = {"bins": []}

        uri = "https://waste.southhams.gov.uk/mycollections"

        s = requests.session()
        r = s.get(uri)
        for cookie in r.cookies:
            if cookie.name == "fcc_session_cookie":
                fcc_session_token = cookie.value

        uri = "https://waste.southhams.gov.uk/mycollections/getcollectiondetails"

        params = {
            "fcc_session_token": fcc_session_token,
            "uprn": user_uprn,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
            "Referer": "https://waste.southhams.gov.uk/mycollections",
            "X-Requested-With": "XMLHttpRequest",
        }

        # Send a POST request with form data and headers
        r = s.post(uri, data=params, headers=headers)

        result = r.json()

        for collection in result["binCollections"]["tile"]:

            # Parse the HTML with BeautifulSoup
            soup = BeautifulSoup(collection[0], "html.parser")
            soup.prettify()

            # Find all collectionDiv elements
            collections = soup.find_all("div", class_="collectionDiv")

            # Process each collectionDiv
            for collection in collections:
                # Extract the service name
                service_name = collection.find("h3").text.strip()

                # Extract collection frequency and day
                details = collection.find("div", class_="detWrap").text.strip()

                # Extract the next collection date
                next_collection = details.split("Your next scheduled collection is ")[
                    1
                ].split(".")[0]

                if next_collection.startswith("today"):
                    next_collection = next_collection.split("today, ")[1]
                elif next_collection.startswith("tomorrow"):
                    next_collection = next_collection.split("tomorrow, ")[1]

                dict_data = {
                    "type": service_name,
                    "collectionDate": datetime.strptime(
                        next_collection, "%A, %d %B %Y"
                    ).strftime(date_format),
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
