import requests
import json
import urllib.parse
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

        headers = {
            "authority": "www.wyre.gov.uk",
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-language": "en-GB,en;q=0.9",
            "cache-control": "no-cache",
            # 'content-length': '0',
            # 'cookie': 'PHPSESSID=ApMqEd65JEQwNgj2AHeeekU9YA5%2C8Tc8YW-nWYSmWkfYq3mS1nvE1WLzMfeWgyoj',
            "origin": "https://www.wyre.gov.uk",
            "pragma": "no-cache",
            "referer": "https://www.wyre.gov.uk/bincollections",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
        }

        api_url = f"https://www.wyre.gov.uk/bincollections?uprn={user_uprn}"
        res = requests.get(api_url, headers=headers)

        soup = BeautifulSoup(res.text, features="html.parser")
        soup.prettify()

        bins = soup.find_all("div", {"class": "boxed"})

        for item in bins:
            heading = item.find("h3", {"class": "bin-collection-tasks__heading"})
            content = item.find("div", {"class": "bin-collection-tasks__content"})
            if not heading or not content:
                continue

            heading_text = " ".join(heading.get_text(" ", strip=True).split())
            title_match = re.search(
                r"Your next\s+(.+?)\s+collection", heading_text, re.IGNORECASE
            )
            if not title_match:
                continue
            collection_title = title_match.group(1).strip()

            date_text = " ".join(content.get_text(" ", strip=True).split())
            date_text = remove_ordinal_indicator_from_date_string(date_text)
            try:
                collection_date = datetime.strptime(date_text, "%A %d %B")
            except ValueError:
                continue

            next_collection = collection_date.replace(year=datetime.now().year)
            if next_collection.date() < datetime.now().date():
                next_collection = next_collection + relativedelta(years=1)
            collections.append((collection_title, next_collection))

        ordered_data = sorted(collections, key=lambda x: x[1])
        for item in ordered_data:
            dict_data = {
                "type": item[0].capitalize(),
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
