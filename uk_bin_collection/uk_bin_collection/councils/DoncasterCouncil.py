import json
import math
from datetime import timedelta

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

        # I need to point out that this one gave me a good head scratch. Mainly because I wrote lots
        # of code to parse the form and all that, then realised this url returns json data... oops.
        base_url = "https://www.doncaster.gov.uk/Compass/PremiseDetail/GetCollectionsForCalendar"

        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        # Working with epoch times, otherwise known as posix/unix timestamps. The number of weeks
        # to return can actually be customised in the below timedelta
        today = math.floor(datetime.today().timestamp())
        four_weeks = math.floor((datetime.today() + timedelta(days=4 * 7)).timestamp())

        # For some reason, the actual web form uses a property id that's completely different
        # from the uprn - luckily this one is easy to find!
        params = {
            'UPRN':  user_uprn,
            'Start': str(today),
            'End':   str(four_weeks),
        }

        response = requests.get(base_url, params=params)

        # Load the json results
        json_results = json.loads(response.text)["slots"]

        data = {"bins": []}
        collections = []

        # Each item is a dictionary, so accessing is easy
        for item in json_results:
            bin_type = item["title"]

            # item["start"] actually returns a string, so we want to only take digits or +s.
            # OK, we don't actually want the +s... or anything on the end of them, that's why
            # we split the string then cast the remaining epoch to a float
            epoch = (''.join([i for i in item["start"] if i.isdigit() or i == "+"]))
            epoch = epoch.split("+")[0]
            epoch = float(epoch)
            bin_date = datetime.strptime(str(datetime.fromtimestamp(epoch / 1000)), "%Y-%m-%d %H:%M:%S")
            collections.append((bin_type, bin_date))

            # This orders the data we just parsed to date order
            ordered_data = sorted(collections, key=lambda x: x[1])
            data = {"bins": []}
            for bin in ordered_data:
                dict_data = {
                    "type":           bin[0],
                    "collectionDate": bin[1].strftime(date_format),
                }
                data["bins"].append(dict_data)

        return data
