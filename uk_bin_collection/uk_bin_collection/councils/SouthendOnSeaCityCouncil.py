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
        data = {"bins": []}

        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        api_url = f"https://apps.cloud9technologies.com/southend/citizenmobile/openapi/wastecollections/{user_uprn}"

        response = requests.get(api_url)
        if response.status_code != 200:
            raise ConnectionError(
                f"Could not fetch waste collection data for UPRN {user_uprn} "
                f"(status {response.status_code})"
            )

        json_data = response.json()
        collection_data = json_data.get("WasteCollectionDates", {})

        # The API returns Container1CollectionDetails through
        # Container11CollectionDetails. Each non-null entry has:
        #   ContainerDescription: str  (e.g. "Refuse Bin")
        #   CollectionDate: str        (e.g. "2026-05-29T00:00:00")
        for i in range(1, 12):
            container = collection_data.get(f"Container{i}CollectionDetails")
            if container is None:
                continue

            bin_type = container.get("ContainerDescription", "Unknown Bin")
            collection_date_str = container.get("CollectionDate")
            if not collection_date_str:
                continue

            collection_date = datetime.strptime(
                collection_date_str, "%Y-%m-%dT%H:%M:%S"
            )

            data["bins"].append(
                {
                    "type": bin_type,
                    "collectionDate": collection_date.strftime(date_format),
                }
            )

        return data
