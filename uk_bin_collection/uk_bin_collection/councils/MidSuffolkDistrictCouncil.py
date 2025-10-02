import re
import time

import holidays
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
        garden_collection_week = kwargs.get("postcode")
        garden_collection_day = kwargs.get("uprn")
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

        garden_week = ["Week 1", "Week 2"]

        refusestartDate = datetime(2024, 11, 11)
        recyclingstartDate = datetime(2024, 11, 4)

        offset_days = days_of_week.index(collection_day)
        offset_days_garden = days_of_week.index(garden_collection_day)
        if garden_collection_week:
            garden_collection = garden_week.index(garden_collection_week)

        refuse_dates = get_dates_every_x_days(refusestartDate, 14, 28)
        recycling_dates = get_dates_every_x_days(recyclingstartDate, 14, 28)

        # Generate bank holidays dynamically using the holidays library
        def get_bank_holidays_set():
            """Get set of bank holiday dates for quick lookup."""
            current_year = datetime.now().year
            uk_holidays = holidays.UK(years=range(current_year - 1, current_year + 3))
            return set(uk_holidays.keys())

        def find_next_collection_day(original_date):
            """Find the next valid collection day, avoiding weekends and bank holidays."""
            bank_holiday_dates = get_bank_holidays_set()
            check_date = datetime.strptime(original_date, "%d/%m/%Y")

            # Safety limit to prevent infinite loops
            max_attempts = 10
            attempts = 0

            # Keep moving forward until we find a valid collection day
            while attempts < max_attempts:
                attempts += 1

                # Check if it's a weekend (Saturday=5, Sunday=6)
                if check_date.weekday() >= 5:
                    check_date += timedelta(days=1)
                    continue

                # Check if it's a bank holiday
                if check_date.date() in bank_holiday_dates:
                    # Major holidays (Christmas/New Year) get bigger delays
                    holiday_name = str(holidays.UK().get(check_date.date(), ''))
                    is_major_holiday = (
                        'Christmas' in holiday_name or
                        'Boxing' in holiday_name or
                        'New Year' in holiday_name
                    )
                    delay_days = 2 if is_major_holiday else 1
                    check_date += timedelta(days=delay_days)
                    continue

                # Found a valid collection day
                break

            # If we've exhausted attempts, return the original date as fallback
            if attempts >= max_attempts:
                return original_date

            return check_date.strftime("%d/%m/%Y")

        bank_holidays = []  # No longer needed - using smart date calculation

        for refuseDate in refuse_dates:
            # Calculate initial collection date
            initial_date = (
                datetime.strptime(refuseDate, "%d/%m/%Y") + timedelta(days=offset_days)
            ).strftime("%d/%m/%Y")

            # Find the next valid collection day (handles weekends + cascading holidays)
            collection_date = find_next_collection_day(initial_date)

            dict_data = {
                "type": "Refuse Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        for recyclingDate in recycling_dates:
            # Calculate initial collection date
            initial_date = (
                datetime.strptime(recyclingDate, "%d/%m/%Y")
                + timedelta(days=offset_days)
            ).strftime("%d/%m/%Y")

            # Find the next valid collection day (handles weekends + cascading holidays)
            collection_date = find_next_collection_day(initial_date)

            dict_data = {
                "type": "Recycling Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        if garden_collection_week:
            if garden_collection == 0:
                gardenstartDate = datetime(2024, 11, 11)
            elif garden_collection == 1:
                gardenstartDate = datetime(2024, 11, 4)

            garden_dates = get_dates_every_x_days(gardenstartDate, 14, 28)

            def is_christmas_period(date_obj):
                """Check if date is in Christmas/New Year skip period for garden collections."""
                if date_obj.month == 12 and date_obj.day >= 23:
                    return True
                if date_obj.month == 1 and date_obj.day <= 3:
                    return True
                return False

            for gardenDate in garden_dates:
                # Calculate initial collection date
                initial_date = (
                    datetime.strptime(gardenDate, "%d/%m/%Y")
                    + timedelta(days=offset_days_garden)
                )

                # Skip garden collections during Christmas/New Year period
                if is_christmas_period(initial_date):
                    continue

                # Find the next valid collection day (handles weekends + holidays)
                collection_date = find_next_collection_day(initial_date.strftime("%d/%m/%Y"))

                dict_data = {
                    "type": "Garden Bin",
                    "collectionDate": collection_date,
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
