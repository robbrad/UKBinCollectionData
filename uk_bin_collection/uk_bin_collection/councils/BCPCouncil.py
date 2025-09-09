import time

import requests
from dateutil.relativedelta import relativedelta

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
        # Make a BS4 object
        uprn = kwargs.get("uprn")
        # usrn = kwargs.get("paon")
        check_uprn(uprn)
        # check_usrn(usrn)
        bindata = {"bins": []}

        # uprn = uprn.zfill(12)

        API_URL = "https://prod-17.uksouth.logic.azure.com/workflows/58253d7b7d754447acf9fe5fcf76f493/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=TAvYIUFj6dzaP90XQCm2ElY6Cd34ze05I3ba7LKTiBs"

        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://bcpportal.bcpcouncil.gov.uk/",
        }
        s = requests.session()
        data = {
            "uprn": uprn,
        }

        r = s.post(API_URL, json=data, headers=headers)
        r.raise_for_status()

        data = r.json()
        rows_data = data["data"]
        for row in rows_data:
            bin_type = row["wasteContainerUsageTypeDescription"]
            collections = row["scheduleDateRange"]
            for collection in collections:
                dict_data = {
                    "type": bin_type,
                    "collectionDate": datetime.strptime(
                        collection, "%Y-%m-%d"
                    ).strftime(date_format),
                }
                bindata["bins"].append(dict_data)

        return bindata
