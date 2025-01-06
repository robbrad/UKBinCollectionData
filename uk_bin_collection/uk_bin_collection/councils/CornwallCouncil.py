from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta

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
        data = {"bins": []}
        collections = []

        curr_date = datetime.today()

        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-GB,en;q=0.9",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.143 Safari/537.36",
            "sec-ch-ua": '"Opera GX";v="111", "Chromium";v="125", "Not.A/Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        params = {
            "uprn": f"{user_uprn}",
            # 'uprn': f'100040128734',
        }
        response = requests.get(
            "https://www.cornwall.gov.uk/umbraco/surface/waste/MyCollectionDays",
            params=params,
            headers=headers,
        )

        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        for item in soup.find_all("div", class_="collection text-center service"):
            bin_type = item.contents[1].text + " bin"
            try:
                collection_date = datetime.strptime(
                    item.contents[5].text, "%d %b"
                ).replace(year=curr_date.year)
            except:
                continue

            if curr_date.month == 12 and collection_date.month == 1:
                collection_date = collection_date + relativedelta(years=1)
            collections.append((bin_type, collection_date))

            ordered_data = sorted(collections, key=lambda x: x[1])
            data = {"bins": []}
            for bin in ordered_data:
                dict_data = {
                    "type": bin[0].capitalize().strip(),
                    "collectionDate": bin[1].strftime(date_format),
                }
                data["bins"].append(dict_data)

        return data
