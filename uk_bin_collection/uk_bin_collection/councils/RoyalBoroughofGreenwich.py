import time

import requests

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

        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)
        check_paon(user_paon)
        bindata = {"bins": []}

        headers = {
            "Origin": "https://www.royalgreenwich.gov.uk/",
            "Referer": "https://www.royalgreenwich.gov.uk/info/200171/recycling_and_rubbish/100/bin_collection_days",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)",
        }

        user_postcode = user_postcode.replace(" ", "+")

        URI = f"https://www.royalgreenwich.gov.uk/site/custom_scripts/apps/waste-collection/new2023/source.php?term={user_postcode}"

        # Make the GET request
        response = requests.get(URI, headers=headers)

        for address in response.json():
            if user_paon in address:
                collection_address = address
                break

        URI = "https://www.royalgreenwich.gov.uk/site/custom_scripts/repo/apps/waste-collection/new2023/ajax-response-uprn.php"

        data = {"address": collection_address}

        response = requests.post(URI, data=data, headers=headers)

        response = response.json()

        collection_day = response["Day"]
        week = response["Frequency"]

        days_of_week = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        collectionweek = ["Week A", "Week B"]

        offset_days = days_of_week.index(collection_day)
        week = collectionweek.index(week)

        greenstartDate = datetime(2024, 11, 25)
        bluestartDate = datetime(2024, 11, 25)
        if week == 0:
            blackstartDate = datetime(2024, 11, 18)
        elif week == 1:
            blackstartDate = datetime(2024, 11, 25)

        green_dates = get_dates_every_x_days(greenstartDate, 7, 100)
        blue_dates = get_dates_every_x_days(bluestartDate, 7, 100)
        black_dates = get_dates_every_x_days(blackstartDate, 14, 50)

        for greenDate in green_dates:

            collection_date = (
                datetime.strptime(greenDate, "%d/%m/%Y") + timedelta(days=offset_days)
            ).strftime("%d/%m/%Y")

            dict_data = {
                "type": "Green Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        for blueDate in blue_dates:

            collection_date = (
                datetime.strptime(blueDate, "%d/%m/%Y") + timedelta(days=offset_days)
            ).strftime("%d/%m/%Y")

            dict_data = {
                "type": "Blue Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        for blackDate in black_dates:

            collection_date = (
                datetime.strptime(blackDate, "%d/%m/%Y") + timedelta(days=offset_days)
            ).strftime("%d/%m/%Y")

            dict_data = {
                "type": "Black Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
