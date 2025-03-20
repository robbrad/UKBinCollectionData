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

        user_paon = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        check_postcode(user_postcode)
        check_paon(user_paon)
        bindata = {"bins": []}

        URI = "https://waste-api-hackney-live.ieg4.net/f806d91c-e133-43a6-ba9a-c0ae4f4cccf6/property/opensearch"

        data = {
            "Postcode": user_postcode,
        }
        headers = {"Content-Type": "application/json"}

        # Make the GET request
        response = requests.post(URI, json=data, headers=headers)

        addresses = response.json()

        for address in addresses["addressSummaries"]:
            summary = address["summary"]
            if user_paon in summary:
                systemId = address["systemId"]
        if systemId:
            URI = f"https://waste-api-hackney-live.ieg4.net/f806d91c-e133-43a6-ba9a-c0ae4f4cccf6/alloywastepages/getproperty/{systemId}"

            response = requests.get(URI)

            address = response.json()

            binIDs = address["providerSpecificFields"][
                "attributes_wasteContainersAssignableWasteContainers"
            ]
            for binID in binIDs.split(","):
                URI = f"https://waste-api-hackney-live.ieg4.net/f806d91c-e133-43a6-ba9a-c0ae4f4cccf6/alloywastepages/getbin/{binID}"
                response = requests.get(URI)
                getBin = response.json()

                bin_type = getBin["subTitle"]

                URI = f"https://waste-api-hackney-live.ieg4.net/f806d91c-e133-43a6-ba9a-c0ae4f4cccf6/alloywastepages/getcollection/{binID}"
                response = requests.get(URI)
                getcollection = response.json()

                collectionID = getcollection["scheduleCodeWorkflowIDs"][0]

                URI = f"https://waste-api-hackney-live.ieg4.net/f806d91c-e133-43a6-ba9a-c0ae4f4cccf6/alloywastepages/getworkflow/{collectionID}"
                response = requests.get(URI)
                collection_dates = response.json()

                dates = collection_dates["trigger"]["dates"]

                for date in dates:
                    parsed_datetime = datetime.strptime(
                        date, "%Y-%m-%dT%H:%M:%SZ"
                    ).strftime(date_format)

                    dict_data = {
                        "type": bin_type.strip(),
                        "collectionDate": parsed_datetime,
                    }
                    bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
