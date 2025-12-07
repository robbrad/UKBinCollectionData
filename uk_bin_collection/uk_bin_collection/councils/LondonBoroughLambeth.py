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

        """
        Parse bin collection data for a given UPRN from the Lambeth waste service API.
        
        Posts the UPRN to the Lambeth "GetServicesByUprn" endpoint, extracts services that include a next collection date and a container, normalizes commercial container types to either "recycling" (if the container name contains "Recycling") or "refuse", and returns a dictionary with a "bins" list where each entry contains the bin type and the collection date formatted according to `date_format`.
        
        Parameters:
            page (str): HTML or page content provided to the parser (not used by this implementation).
            uprn (str, optional, in kwargs): The UPRN to query; required in kwargs as "uprn".
        
        Returns:
            dict: A dictionary with a single key "bins" mapping to a list of objects with:
                - "type" (str): Bin type (e.g., "recycling", "refuse", or the container's DisplayPhrase).
                - "collectionDate" (str): Collection date formatted using `date_format`.
        
        Raises:
            ConnectionRefusedError: If the API response status code is not 200.
        """
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