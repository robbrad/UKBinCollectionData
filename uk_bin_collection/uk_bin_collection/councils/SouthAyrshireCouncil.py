import json
from datetime import timedelta

import requests
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # Get and check both the passed UPRN and postcode
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        user_postcode = kwargs.get("postcode")
        check_postcode(user_postcode)

        # Build the headers, specify the parameters and then make a GET for the calendar
        headers = {
            "Connection": "Keep-Alive",
            "User-Agent": "okhttp/3.14.9",
        }
        params = {
            "end_date": "2024-01-01",
            "rn": user_uprn,
            "device": "undefined",
            "postcode": user_postcode,
            "OS": "android",
            "OS_ver": "31",
            "app_ver": "35",
        }
        requests.packages.urllib3.disable_warnings()
        response = requests.get(
            "http://www.sac-bins.co.uk/get_calendar.php", params=params, headers=headers
        )

        # Load the response as JSON
        json_data = json.loads(response.text)

        # The response loads well over a year's worth of data, so figure out some dates to limit output
        today = datetime.today()
        eight_weeks = datetime.today() + timedelta(days=8 * 7)
        data = {"bins": []}

        # The bin titles are pretty weird and colours are too basic, so make the names match the app
        bin_friendly_names = {
            "blue": "Blue Bin",
            "red": "Food Caddy",
            "green": "Green Bin",
            "grey": "Grey Bin",
            "purple": "Purple Bin",
            "brown": "Brown Bin",
        }

        # Loop through the results. When a date is found that's on or greater than today's date AND less than
        # eight weeks away, we want it in the output. So look up the friendly name and add it in.
        for item in json_data:
            bin_date = datetime.strptime(item["start"], "%Y-%m-%d").date()
            if today.date() <= bin_date <= eight_weeks.date():
                bin_type = bin_friendly_names.get(item["className"])
                dict_data = {
                    "type": bin_type,
                    "collectionDate": bin_date.strftime(date_format),
                }
                data["bins"].append(dict_data)

        return data
