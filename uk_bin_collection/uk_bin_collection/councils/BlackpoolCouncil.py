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
        user_postcode = kwargs.get("postcode")
        check_uprn(user_uprn)
        check_postcode(user_postcode)
        bindata = {"bins": []}

        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-GB,en;q=0.9",
            "Connection": "keep-alive",
            "DNT": "1",
            "Origin": "https://www.blackpool.gov.uk",
            "Referer": "https://www.blackpool.gov.uk/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }

        response = requests.get(
            "https://api.blackpool.gov.uk/live//api/bartec/security/token",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()

        token = response.text.strip().replace('"', "")

        json_data = {
            "UPRN": user_uprn,
            "USRN": "",
            "PostCode": user_postcode,
            "StreetNumber": "",
            "CurrentUser": {
                "UserId": "",
                "Token": token,
            },
        }

        response = requests.post(
            "https://api.blackpool.gov.uk/live//api/bartec/collection/PremiseJobs",
            headers=headers,
            json=json_data,
        )

        # Parse the JSON response
        bin_collection = response.json()

        # Loop through each collection in bin_collection
        for collection in bin_collection["jobsField"]:

            job = collection["jobField"]
            date = job.get("scheduledStartField")
            bin_type = job.get("nameField", "") or job.get("descriptionField", "")

            dict_data = {
                "type": bin_type,
                "collectionDate": datetime.strptime(
                    date,
                    "%Y-%m-%dT%H:%M:%S",
                ).strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
