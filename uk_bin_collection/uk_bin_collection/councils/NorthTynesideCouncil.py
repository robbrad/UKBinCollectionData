import math
from datetime import *

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):

    def parse_data(self, page: str, **kwargs) -> dict:

        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        check_uprn(user_uprn)
        check_postcode(user_postcode)

        requests.packages.urllib3.disable_warnings()
        s = requests.Session()

        # Get the first form
        response = s.get(
            "https://my.northtyneside.gov.uk/category/81/bin-collection-dates",
            verify = False,
        )

        # Find the form ID and submit with a postcode
        soup = BeautifulSoup(response.text, features="html.parser")
        form_build_id = soup.find("input", {"name": "form_build_id"})["value"]
        response = s.post(
            "https://my.northtyneside.gov.uk/category/81/bin-collection-dates",
            data = {
                "postcode": user_postcode,
                "op": "Find",
                "form_build_id": form_build_id,
                "form_id": "ntc_address_wizard",
            },
            verify = False,
        )

        # Find the form ID and submit with the UPRN
        soup = BeautifulSoup(response.text, features="html.parser")
        form_build_id = soup.find("input", {"name": "form_build_id"})["value"]
        response = s.post(
            "https://my.northtyneside.gov.uk/category/81/bin-collection-dates",
            data = {
                "house_number": f"0000{user_uprn}",
                "op": "Use",
                "form_build_id": form_build_id,
                "form_id": "ntc_address_wizard",
            },
            verify = False,
        )

        # Parse form page and get the day of week and week offsets
        soup = BeautifulSoup(response.text, features="html.parser")
        info_section  = soup.find("section", {"class": "block block-ntc-bins clearfix"})

        # Get day of week and week label for refuse, garden and special collections.
        # Week label is A or B.  Convert that to an int to use as an offset.
        for anchor in info_section.findAll("a"):
            if anchor.text.startswith("Refuse and Recycling"):
                regular_day = anchor.text.strip().split()[-3]
                if anchor.text.strip().split()[-1] == "A":
                    regular_week = 0
                else:
                    regular_week = 1
            elif anchor.text.startswith("Garden Waste"):
                garden_day = anchor.text.strip().split()[-3]
                if anchor.text.strip().split()[-1] == "A":
                    garden_week = 0
                else:
                    garden_week = 1
        for para in info_section.findAll("p"):
            if para.text.startswith("Your special collections day"):
                special_day = para.find("strong").text.strip()

        # The regular calendar only shows until end of March 2026, work out how many weeks that is
        weeks_total = math.floor((datetime(2026, 4, 1) - datetime.now()).days / 7)

        # The garden calendar only shows until end of November 2024, work out how many weeks that is
        garden_weeks_total = math.floor((datetime(2024, 12, 1) - datetime.now()).days / 7)

        # Convert day text to series of dates using previous calculation
        regular_collections = get_weekday_dates_in_period(
            datetime.today(),
            days_of_week.get(regular_day.capitalize()),
            amount=weeks_total,
        )
        garden_collections = get_weekday_dates_in_period(
            datetime.today(),
            days_of_week.get(garden_day.capitalize()),
            amount=garden_weeks_total,
        )
        special_collections = get_weekday_dates_in_period(
            datetime.today(),
            days_of_week.get(special_day.capitalize()),
            amount=weeks_total,
        )

        collections = []

        # Add regular collections, and differentiate between regular and recycling bins
        for item in regular_collections:
            item_as_date = datetime.strptime(item, date_format)
            # Check if holiday (calendar only has one day that's a holiday, and it's moved to the next day)
            if is_holiday(item_as_date, Region.ENG):
                item_as_date += timedelta(days=1)
            # Use the isoweek number to separate collections based on week label.
            if (item_as_date.date().isocalendar()[1] % 2) == regular_week:
                collections.append(("Refuse (green)", item_as_date))
            else:
                collections.append(("Recycling (grey)", item_as_date))

        # Add garden collections
        for item in garden_collections:
            item_as_date = datetime.strptime(item, date_format)
            # Garden collections do not move for bank holidays
            if (item_as_date.date().isocalendar()[1] % 2) == garden_week:
                collections.append(("Garden Waste (brown)", item_as_date))

        # Add special collections
        collections += [
            ("Special Collection (bookable)", datetime.strptime(item, date_format))
            for item in special_collections
        ]

        return {
            "bins": [
                    {
                    "type": item[0],
                    "collectionDate": item[1].strftime(date_format),
                }
                for item in sorted(collections, key=lambda x: x[1])
            ]
        }