import logging
import re
import warnings
from datetime import datetime

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

_LOGGER = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class CouncilClass(AbstractGetBinDataClass):
    # Durham exposes bin data via a JSON-RPC POST endpoint rather than a
    # static page, so this scraper fetches its own data and ignores the
    # `page` arg. input.json sets skip_get_url=true to avoid a wasted GET.
    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        response = requests.post(
            "https://www.durham.gov.uk/apiserver/ajaxlibrary/",
            json={
                "jsonrpc": "2.0",
                "method": "durham.Localities.GetBartecCalendar",
                "params": {"uprn": uprn},
                "id": "21",
                "name": "V2 AJAX End Point Library Worker",
            },
        )
        response.raise_for_status()
        xml_string = response.json()["result"]

        soup = BeautifulSoup(xml_string, "html.parser")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Format comes back as, for example: "Empty Bin Refuse 240L" 
        # Futureproof regex to match:
        # Optional "Empty Bin " prefix, capture bin label, optional " 240L"
        # volume suffix. Whitespace is flexible throughout.
        name_pattern = re.compile(
            r"(?:Empty\s+Bin\s+)?(.+?)(?:\s+\d+\s*[Ll])?$"
        )

        next_dates = {}
        for job in soup.find_all("job"):
            name_tag = job.find("name")
            start_tag = job.find("scheduledstart")
            if not name_tag or not start_tag:
                continue

            raw_name = name_tag.get_text(strip=True)
            match = name_pattern.search(raw_name)
            if not match:
                _LOGGER.warning("Could not parse bin name %r", raw_name)
                continue
            label = match.group(1).strip()

            try:
                scheduled = datetime.strptime(
                    start_tag.get_text(strip=True)[:10], "%Y-%m-%d"
                )
            except ValueError:
                _LOGGER.warning(
                    "Could not parse scheduled date %r for bin %r",
                    start_tag.get_text(strip=True),
                    raw_name,
                )
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
