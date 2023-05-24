import hashlib
import math
import time
from datetime import timedelta

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


def ct(e: str) -> int:
    """
    Mimic ct() function in main.cbc0dd8a.js
        :rtype: int
        :param e: Day name
        :return: Day index
    """
    if e == "MON":
        return 0
    elif e == "TUE":
        return 1
    elif e == "WED":
        return 2
    elif e == "THU":
        return 3
    elif e == "FRI":
        return 4
    return -1


def ft() -> dict:
    """
    Mimic ft() function in main.cbc0dd8a.js
        :rtype: dict
        :return: Weeks and days
    """
    e = datetime.now()
    t = datetime(2022, 4, 20)
    return {
        "weeks": math.floor(((e - t).total_seconds() * 10) / 1e3 / 86400 / 7 % 2),
        "days": math.floor(((e - t).total_seconds() * 10) / 1e3 / 86400 % 7),
    }


def st(e: int, t: int, n: str) -> str:
    """
    Mimic st() function in main.cbc0dd8a.js
        :rtype: str
        :return: Date
    """
    d = datetime.now() + timedelta(days=(7 * t + (e - n)))
    return d.strftime(date_format)


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)",
            "origin": "https://kbccollectiveapi-coll-api.e4ff.pro-eu-west-1.openshiftapps.com",
            "referer": "https://kbccollectiveapi-coll-api.e4ff.pro-eu-west-1.openshiftapps.com/",
        }
        requests.packages.urllib3.disable_warnings()
        # Check council website workings haven't changed
        response = requests.get(
            f"https://kbccollectiveapi-coll-api.e4ff.pro-eu-west-1.openshiftapps.com/wc-info/static/js/main.cbc0dd8a.js",
            headers=headers,
        )
        if (
            response.status_code != 200
            or hashlib.sha256(response.text.encode("utf-8")).hexdigest()
            != "2f357c24b043c31c0157c234323c401238842c1d00f00f16c7ca3e569a0ab3cd"
        ):
            raise ValueError(
                "Council website has changed, parser needs updating. Please open issue on GitHub."
            )
        # Get variables for workings
        response = requests.get(
            f"https://api.northnorthants.gov.uk/test/wc-info/{uprn}?r={time.time() * 1000}",
            headers=headers,
        )
        if response.status_code != 200:
            raise ValueError("No bin data found for provided UPRN.")

        json_response = json.loads(response.text)
        sov = json_response["sov"]
        day = json_response["day"]
        schedule = json_response["schedule"]
        # Mimic workings in main.cbc0dd8a.js
        if sov == "ENC" or sov == "BCW":
            n = ft()
            r = 1
            if ct(day) > n["days"]:
                r = 0
            for o in range(0, 10):
                week = (n["weeks"] + o + r) % 2
                if (week == 0 and "B" == schedule) or (week != 0 and "B" != schedule):
                    bin_type = "General"
                else:
                    bin_type = "Recycling"
                collection_data = {
                    "type": bin_type,
                    "nextCollectionDate": st(ct(day), o + r, n["days"]).replace(
                        ",", ""
                    ),
                }
                data["bins"].append(collection_data)

        return data
