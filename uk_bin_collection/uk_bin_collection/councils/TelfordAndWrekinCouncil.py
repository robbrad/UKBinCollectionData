import requests
import json

from dateutil.relativedelta import relativedelta
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
        collections = []
        api_url = f"https://dac.telford.gov.uk/BinDayFinder/Find/PropertySearch?uprn={user_uprn}"

        response = requests.get(api_url)
        if response.status_code != 200:
            raise ConnectionError("Could not get latest data!")

        json_data = json.loads(response.text.replace("\\", "")[1:-1])["bincollections"]
        for item in json_data:
            collection_date = datetime.strptime(
                remove_ordinal_indicator_from_date_string(item.get("nextDate")),
                "%A %d %B",
            )
            next_collection = collection_date.replace(year=datetime.now().year)
            if datetime.now().month == 12 and next_collection.month == 1:
                next_collection = next_collection + relativedelta(years=1)

            collections.append((item.get("name"), next_collection))

        ordered_data = sorted(collections, key=lambda x: x[1])
        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
