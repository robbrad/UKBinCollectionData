import requests
from requests.structures import CaseInsensitiveDict

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
        data = {"bins": []}

        url = "https://wasteservice.lambeth.gov.uk/WhitespaceComms/GetServicesByUprn"

        headers = CaseInsensitiveDict()
        headers["Content-Type"] = "application/json"

        body = {"uprn": user_uprn, "includeEventTypes": False, "includeFlags": True}
        json_data = json.dumps(body)

        res = requests.post(url, headers=headers, data=json_data)

        if res.status_code != 200:
            raise ConnectionRefusedError("Cannot connect to API!")

        json_data = res.json()

        if "SiteServices" in json_data:
            SiteServices = json_data["SiteServices"]
            for service in SiteServices:
                if "NextCollectionDate" in service:
                    NextCollectionDate = service["NextCollectionDate"]
                    if NextCollectionDate:
                        Container = service["Container"]
                        if Container:
                            if Container["DisplayPhrase"] == "commercial bin":
                                Bin_Type = (
                                    "recycling"
                                    if "Recycling" in Container["Name"]
                                    else "refuse"
                                )
                            else:
                                Bin_Type = Container["DisplayPhrase"]
                            dict_data = {
                                "type": Bin_Type,
                                "collectionDate": datetime.strptime(
                                    NextCollectionDate, "%d/%m/%Y"
                                ).strftime(date_format),
                            }
                            data["bins"].append(dict_data)

        return data
