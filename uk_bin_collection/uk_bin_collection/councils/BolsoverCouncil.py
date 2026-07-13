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

        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        SESSION_URL = "https://selfservice.bolsover.gov.uk/authapi/isauthenticated?uri=https%253A%252F%252Fselfservice.bolsover.gov.uk%252Fservice%252FCheck_your_Bin_Day&hostname=selfservice.bolsover.gov.uk&withCredentials=true"

        API_URL = "https://selfservice.bolsover.gov.uk/apibroker/runLookup"

        data = {
            "formValues": {"Bin Collection": {"uprnLoggedIn": {"value": user_uprn}}},
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://selfservice.bolsover.gov.uk/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        params = {
            "id": "6023d37e037c3",
            "repeat_against": "",
            "noRetry": "true",
            "getOnlyTokens": "undefined",
            "log_id": "",
            "app_name": "AF-Renderer::Self",
            # unix_timestamp
            "_": str(int(time.time() * 1000)),
            "sid": sid,
        }

        r = s.post(API_URL, json=data, headers=headers, params=params)
        r.raise_for_status()

        data = r.json()
        rows_data = data["integration"]["transformed"]["rows_data"]["0"]
        if not isinstance(rows_data, dict):
            raise ValueError("Invalid data returned from API")

        # print(rows_data)

        route = rows_data["Route"]

        # print(route)

        def get_route_number(route):
            if route[:2] == "Mo":
                return 0
            elif route[:2] == "Tu":
                return 1
            elif route[:2] == "We":
                return 2
            elif route[:2] == "Th":
                return 3
            elif route[:2] == "Fr":
                return 4
            else:
                return None  # Default case if none of the conditions match

        dayOfCollectionAsNumber = get_route_number(route)
        # print(dayOfCollectionAsNumber)

        def calculate_collection_date(
            dayOfCollectionAsNumber,
            currentDayAsNumber,
            today,
            dayDiffPlus,
            dayDiffMinus,
        ):
            if dayOfCollectionAsNumber == currentDayAsNumber:
                return today
            elif dayOfCollectionAsNumber > currentDayAsNumber:
                return today + timedelta(days=dayDiffPlus)
            else:
                return today + timedelta(days=dayDiffMinus)

        # Example usage
        today = datetime.today()  # Current date
        currentDayAsNumber = today.weekday()
        dayDiffPlus = dayOfCollectionAsNumber - currentDayAsNumber
        dayDiffMinus = dayOfCollectionAsNumber - currentDayAsNumber + 7

        week1 = calculate_collection_date(
            dayOfCollectionAsNumber,
            currentDayAsNumber,
            today,
            dayDiffPlus,
            dayDiffMinus,
        )
        week2 = week1 + timedelta(days=7)
        week3 = week2 + timedelta(days=7)
        week4 = week3 + timedelta(days=7)

        # print(week1.strftime(date_format))
        # print(week2.strftime(date_format))
        # print(week3.strftime(date_format))
        # print(week4.strftime(date_format))

        greenSusStart = datetime.strptime("2024-11-08", "%Y-%m-%d")
        greenSusEnd = datetime.strptime("2025-03-18", "%Y-%m-%d")

        def is_within_green_sus(dtDay0, greenSusStart, greenSusEnd):
            return "Yes" if greenSusStart <= dtDay0 < greenSusEnd else "No"

        week1InSus = is_within_green_sus(week1, greenSusStart, greenSusEnd)
        week2InSus = is_within_green_sus(week2, greenSusStart, greenSusEnd)
        week3InSus = is_within_green_sus(week3, greenSusStart, greenSusEnd)
        week4InSus = is_within_green_sus(week4, greenSusStart, greenSusEnd)

        # print(week1InSus)
        # print(week2InSus)
        # print(week3InSus)
        # print(week4InSus)

        WeekBlack = rows_data["WeekBlack"]
        WeekBandG = rows_data["WeekBandG"]

        def determine_bin_collection(week_number, txtBlack, txtBurgGreen, week_in_sus):
            # WeekBlack/WeekBandG aren't booleans - they hold "1" or "2" to
            # say which of the two alternating weeks (odd/even relative to
            # week1) that stream is collected on. Round A addresses have
            # WeekBlack == "1"; Round B addresses have WeekBlack == "2"
            # (and WeekBandG the complementary value).
            parity = "1" if week_number % 2 == 1 else "2"

            if txtBlack == parity:
                return "Black Bin"

            if txtBurgGreen == parity:
                if week_in_sus == "Yes":
                    return "Burgundy Bin"
                return "Burgundy Bin & Green Bin"

            return ""

        week1Text = determine_bin_collection(1, WeekBlack, WeekBandG, week1InSus)
        week2Text = determine_bin_collection(2, WeekBlack, WeekBandG, week2InSus)
        week3Text = determine_bin_collection(3, WeekBlack, WeekBandG, week3InSus)
        week4Text = determine_bin_collection(4, WeekBlack, WeekBandG, week4InSus)

        # print(week1Text)
        # print(week2Text)
        # print(week3Text)
        # print(week4Text)

        week_data = [
            (week1Text, week1),
            (week2Text, week2),
            (week3Text, week3),
            (week4Text, week4),
        ]

        # print(week_data)

        # Iterate through the array
        for week_text, week_date in week_data:
            # Check if '&' exists and split
            if "&" in week_text:
                split_texts = [text.strip() for text in week_text.split("&")]
                for text in split_texts:
                    dict_data = {
                        "type": text,
                        "collectionDate": week_date.strftime(date_format),
                    }
                    bindata["bins"].append(dict_data)
            else:
                dict_data = {
                    "type": week_text,
                    "collectionDate": week_date.strftime(date_format),
                }
                bindata["bins"].append(dict_data)

        return bindata
