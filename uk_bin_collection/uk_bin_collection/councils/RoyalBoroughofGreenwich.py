import logging
import time

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

logger = logging.getLogger(__name__)


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    # Method used to set the year from the holiday adjustments to avoid issues around the new year
    def _set_year_from_month(self, date):
        if date.month < datetime.now().month:
            return date.replace(year=datetime.now().year + 1)
        else:
            return date.replace(year=datetime.now().year)

    def _add_bin_dates(self, dates, bin_type, bindata, holiday_dict, offset_days):
        for date_str in dates:
            collection_date = datetime.strptime(date_str, "%d/%m/%Y") + timedelta(
                days=offset_days
            )
            if collection_date in holiday_dict:
                collection_date = holiday_dict[collection_date]
            dict_data = {
                "type": bin_type,
                "collectionDate": collection_date.strftime("%d/%m/%Y"),
            }
            bindata["bins"].append(dict_data)

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

        # Make the GET request to retrieve the day of the week and black bin week for the address
        response = requests.get(URI, headers=headers, timeout=30)
        response.raise_for_status()

        for address in response.json():
            if user_paon in address:
                collection_address = address
                break

        URI = "https://www.royalgreenwich.gov.uk/site/custom_scripts/repo/apps/waste-collection/new2023/ajax-response-uprn.php"

        data = {"address": collection_address}

        response = requests.post(URI, data=data, headers=headers, timeout=30)
        response.raise_for_status()
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

        # Retrieve the list of dates amended by bank holidays such that we can adjust accordingly
        holiday_dict = {}
        try:
            holiday_URI = "https://www.royalgreenwich.gov.uk/recycling-and-rubbish/bins-and-collections/bank-holiday-collection-dates"
            holiday_response = requests.get(holiday_URI, headers=headers, timeout=30)
            holiday_response.raise_for_status()
            soup = BeautifulSoup(holiday_response.text, features="html.parser")

            table = soup.select_one("table.tablesaw.tablesaw-stack")
            if table:
                rows = table.find("tbody").find_all("tr")
                for row in rows:
                    original_collection_date = row.find_all("td")[0].get_text(
                        strip=True
                    )
                    original_collection_date = re.findall(
                        r"\w+ \d+ \w+", original_collection_date
                    )[0]
                    original_collection_date = datetime.strptime(
                        original_collection_date, "%A %d %B"
                    )

                    original_collection_date = self._set_year_from_month(original_collection_date)

                    new_collection_date = row.find_all("td")[1].get_text(strip=True)
                    new_collection_date = new_collection_date.replace(
                        " (bank holiday)", ""
                    )
                    new_collection_date = datetime.strptime(
                        new_collection_date, "%A %d %B"
                    )
                    # Handle the case where the new collection date is in the next year
                    new_collection_date = self._set_year_from_month(new_collection_date)

                    holiday_dict[original_collection_date] = new_collection_date
        except (
            requests.exceptions.RequestException,
            AttributeError,
            IndexError,
            ValueError,
        ) as e:
            logger.warning(f"Failed to scrape bank holiday dates: {e}")

        greenstartDate = datetime(2025, 12, 29)
        bluestartDate = datetime(2025, 12, 29)
        if week == 0:
            blackstartDate = datetime(2025, 12, 29)
        elif week == 1:
            blackstartDate = datetime(2026, 1, 5)

        green_dates = get_dates_every_x_days(greenstartDate, 7, 100)
        blue_dates = get_dates_every_x_days(bluestartDate, 7, 100)
        black_dates = get_dates_every_x_days(blackstartDate, 14, 50)

        self._add_bin_dates(
            green_dates, "Green Bin", bindata, holiday_dict, offset_days
        )
        self._add_bin_dates(blue_dates, "Blue Bin", bindata, holiday_dict, offset_days)
        self._add_bin_dates(
            black_dates, "Black Bin", bindata, holiday_dict, offset_days
        )

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
