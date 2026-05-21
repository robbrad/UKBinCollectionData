import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from bs4 import XMLParsedAsHTMLWarning
import warnings
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        requests.packages.urllib3.disable_warnings()
        response = requests.post(
            "https://www.durham.gov.uk/apiserver/ajaxlibrary/",
            json={
                "jsonrpc": "2.0",
                "method": "durham.Localities.GetBartecCalendar",
                "params": {"uprn": uprn},
                "id": "21",
                "name": "V2 AJAX End Point Library Worker",
            },
            verify=False,
        )
        response.raise_for_status()

        xml_string = response.json()["result"]
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(xml_string, "html.parser")

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        next_dates = {}

        for job in soup.find_all("job"):
            name_tag = job.find("name")
            start_tag = job.find("scheduledstart")
            if not name_tag or not start_tag:
                continue

            raw_name = name_tag.get_text(strip=True)
            match = re.search(r"Empty Bin (.+?) \d+L", raw_name)
            if not match:
                continue

            label = match.group(1)

            try:
                scheduled = datetime.strptime(
                    start_tag.get_text(strip=True)[:10], "%Y-%m-%d"
                )
            except ValueError:
                continue

            if scheduled < today:
                continue

            if label not in next_dates or scheduled < next_dates[label]:
                next_dates[label] = scheduled

        data = {"bins": []}
        for bin_type, collection_date in next_dates.items():
            data["bins"].append({
                "type": bin_type,
                "collectionDate": collection_date.strftime(date_format),
            })

        return data
