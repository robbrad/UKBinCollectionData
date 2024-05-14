from bs4 import BeautifulSoup
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

        headers = {
            "authority": "www.hull.gov.uk",
            "accept": "*/*",
            "accept-language": "en-GB,en;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "referer": "https://www.hull.gov.uk/bins-and-recycling/bin-collections/bin-collection-day-checker",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.186 Safari/537.36",
        }
        api_url = f"https://www.hull.gov.uk/ajax/bin-collection?bindate={user_uprn}"

        res = requests.get(api_url, headers=headers)
        if res.status_code != 200:
            raise ConnectionRefusedError("Cannot connect to API!")

        json_data = res.json()[0]
        for item in json_data:
            dict_data = {
                "type": item.get("collection_type").capitalize(),
                "collectionDate": datetime.strptime(
                    item.get("next_collection_date"), "%Y-%m-%d"
                ).strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
