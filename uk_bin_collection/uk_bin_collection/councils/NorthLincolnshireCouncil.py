from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Host": "m.northlincs.gov.uk",
            "Origin": "https://www.northlincs.gov.uk",
            "Referer": "https://www.northlincs.gov.uk/",
            "sec-ch-ua": '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        }
        requests.packages.urllib3.disable_warnings()
        response = requests.get(
            f"https://m.northlincs.gov.uk/collection_dates/{uprn}/0/6?_=1546855781728&format=json",
            headers=headers,
        )
        if response.status_code != 200:
            raise ValueError("No bin data found for provided UPRN.")
        json_data = json.loads(response.text)

        data = {"bins": []}
        for c in json_data["Collections"]:
            bin_type = c["BinCodeDescription"].strip()
            if bin_type.lower() != "textiles bag":
                dict_data = {
                    "type": bin_type,
                    "collectionDate": datetime.strptime(
                        c["BinCollectionDate"].replace(" (*)", "").strip()
                        + " "
                        + datetime.now().strftime("%Y"),
                        "%A %d %B %Y",
                    ).strftime(date_format),
                }
                data["bins"].append(dict_data)

        return data
