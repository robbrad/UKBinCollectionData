import json
import requests
from datetime import datetime

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


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
        
        # Make API request
        api_url = f"https://east-herts.co.uk/api/services/{user_uprn}"
        response = requests.get(api_url)
        response.raise_for_status()
        
        data = response.json()
        today = datetime.now().date()
        
        for service in data.get("services", []):
            collection_date_str = service.get("collectionDate")
            if collection_date_str:
                collection_date = datetime.strptime(collection_date_str, "%Y-%m-%d").date()
                # Only include future dates
                if collection_date >= today:
                    dict_data = {
                        "type": service.get("binType", ""),
                        "collectionDate": collection_date.strftime("%d/%m/%Y"),
                    }
                    bindata["bins"].append(dict_data)
        
        return bindata
