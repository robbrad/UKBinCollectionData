import re
import time

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

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

        collection_day = kwargs.get("paon")
        collection_week = kwargs.get("postcode")
        bindata = {"bins": []}

        days_of_week = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        week = ["Week 1", "Week 2"]

        offset_days = days_of_week.index(collection_day)
        collection_week = week.index(collection_week)

        if collection_week == 0:
            refusestartDate = datetime(2024, 11, 25)
            recyclingstartDate = datetime(2024, 11, 18)
        else:
            refusestartDate = datetime(2024, 11, 18)
            recyclingstartDate = datetime(2024, 11, 25)

        refuse_dates = get_dates_every_x_days(refusestartDate, 14, 28)
        recycling_dates = get_dates_every_x_days(recyclingstartDate, 14, 28)
        food_dates = get_dates_every_x_days(recyclingstartDate, 7, 56)

        for refuseDate in refuse_dates:

            collection_date = (
                datetime.strptime(refuseDate, "%d/%m/%Y") + timedelta(days=offset_days)
            ).strftime("%d/%m/%Y")

            dict_data = {
                "type": "Refuse Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        for recyclingDate in recycling_dates:

            collection_date = (
                datetime.strptime(recyclingDate, "%d/%m/%Y")
                + timedelta(days=offset_days)
            ).strftime("%d/%m/%Y")

            dict_data = {
                "type": "Recycling Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

            dict_data = {
                "type": "Garden Waste Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        for food_date in food_dates:

            collection_date = (
                datetime.strptime(food_date, "%d/%m/%Y") + timedelta(days=offset_days)
            ).strftime("%d/%m/%Y")

            dict_data = {
                "type": "Food Waste Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
