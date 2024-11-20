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

        collection_weeks = ["Week 1", "Week 2"]
        collection_week = collection_weeks.index(collection_week)

        offset_days = days_of_week.index(collection_day)

        if collection_week == 0:
            recyclingstartDate = datetime(2024, 11, 4)
            glassstartDate = datetime(2024, 11, 4)
            refusestartDate = datetime(2024, 11, 11)
        elif collection_week == 1:
            recyclingstartDate = datetime(2024, 11, 11)
            glassstartDate = datetime(2024, 11, 11)
            refusestartDate = datetime(2024, 11, 4)

        refuse_dates = get_dates_every_x_days(refusestartDate, 14, 28)
        glass_dates = get_dates_every_x_days(glassstartDate, 14, 28)
        recycling_dates = get_dates_every_x_days(recyclingstartDate, 14, 28)

        for refuseDate in refuse_dates:

            collection_date = (
                datetime.strptime(refuseDate, "%d/%m/%Y") + timedelta(days=offset_days)
            ).strftime("%d/%m/%Y")

            dict_data = {
                "type": "Grey Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        for recyclingDate in recycling_dates:

            collection_date = (
                datetime.strptime(recyclingDate, "%d/%m/%Y")
                + timedelta(days=offset_days)
            ).strftime("%d/%m/%Y")

            dict_data = {
                "type": "Green Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        for glassDate in glass_dates:

            collection_date = (
                datetime.strptime(glassDate, "%d/%m/%Y") + timedelta(days=offset_days)
            ).strftime("%d/%m/%Y")

            dict_data = {
                "type": "Glass Box",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
