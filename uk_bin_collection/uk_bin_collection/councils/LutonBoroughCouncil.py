import time

import requests
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
        bindata = {"bins": []}

        SESSION_URL = "https://myforms.luton.gov.uk/authapi/isauthenticated?uri=https%253A%252F%252Fmyforms.luton.gov.uk%252Fservice%252FFind_my_bin_collection_date&hostname=myforms.luton.gov.uk&withCredentials=true"

        API_URL = "https://myforms.luton.gov.uk/apibroker/runLookup"

        data = {
            "formValues": {
                "Find my bin collection date": {
                    "id": {
                        "value": f"1-{user_uprn}",
                    },
                },
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://myforms.luton.gov.uk/fillform/?iframe_id=fillform-frame-1&db_id=",
        }
        s = requests.session()
        r = s.get(SESSION_URL)
        r.raise_for_status()
        session_data = r.json()
        sid = session_data["auth-session"]
        params = {
            "id": "65cb710f8d525",
            "repeat_against": "",
            "noRetry": "true",
            "getOnlyTokens": "undefined",
            "log_id": "",
            "app_name": "AF-Renderer::Self",
            # unix_timestamp
            "_": str(int(time.time() * 1000)),
            "sid": sid,
        }
        r = s.post(API_URL, json=data, headers=headers, params=params)
        r.raise_for_status()
        data = r.json()
        rows_data = data["integration"]["transformed"]["rows_data"][f"{user_uprn}"]

        soup = BeautifulSoup(rows_data["html"], features="html.parser")
        soup.prettify()
        for collection in soup.find_all("tr"):
            tds = collection.find_all("td")
            bin_type = tds[1].text
            collection_date = datetime.strptime(
                tds[0].text,
                "%A %d %b %Y",
            )
            dict_data = {
                "type": bin_type,
                "collectionDate": collection_date.strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        return bindata
