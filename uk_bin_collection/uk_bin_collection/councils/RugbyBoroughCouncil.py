import requests

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

        api_url = (
            "https://apps.cloud9technologies.com/rugby/citizenmobile/webapi/"
            f"wastecollections/{user_uprn}"
        )
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        json_data = response.json()

        waste_collection_dates = json_data["wasteCollectionDates"]

        data = {"bins": []}

        for key, collection in waste_collection_dates.items():
            if not key.startswith("container") or not collection:
                continue

            collection_date = datetime.fromisoformat(collection["collectionDate"])

            dict_data = {
                "type": collection["containerDescription"],
                "collectionDate": collection_date.strftime(date_format),
            }
            data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
