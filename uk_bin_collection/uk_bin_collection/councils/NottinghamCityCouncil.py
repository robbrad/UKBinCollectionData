from bs4 import BeautifulSoup
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

        api_url = f"https://geoserver.nottinghamcity.gov.uk/myproperty/handler/proxy.ashx?https://geoserver.nottinghamcity.gov.uk/bincollections2/api/collection/{user_uprn}"

        requests.packages.urllib3.disable_warnings()
        response = requests.get(api_url)
        json_data = json.loads(response.text)
        data = {"bins": []}

        next_collections = json_data["nextCollections"]

        for collection in next_collections:
            bin_type = collection["collectionType"]

            next_collection_date = datetime.fromisoformat(collection["collectionDate"])
            dict_data = {
                "type": bin_type,
                "collectionDate": next_collection_date.strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
