from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        # The seasonal `-xmas2025` variant has been retired. The evergreen
        # endpoint is `collection-result-soap.asp`. The council website also
        # geoblocks datacentre traffic, so callers needing a live request
        # should route through a residential proxy.
        uri = (
            "https://www.conwy.gov.uk/Contensis-Forms/erf/collection-result-soap.asp"
            f"?ilangid=1&uprn={user_uprn}"
        )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                " (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
            )
        }
        # www.conwy.gov.uk intermittently returns connection resets, read
        # timeouts, or SSL handshake failures depending on load. Do two
        # short attempts so a flaky request still fits the production budget.
        import time as _time
        response = None
        last_err = None
        for attempt in range(2):
            try:
                response = requests.get(
                    uri, headers=headers, timeout=15, verify=False,
                )
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                last_err = e
                response = None
                if attempt == 0:
                    _time.sleep(2)
        if response is None:
            raise last_err  # type: ignore[misc]
        soup = BeautifulSoup(response.content, features="html.parser")
        data = {"bins": []}

        for bin_section in soup.select('div[class*="containererf"]'):
            date_text = bin_section.find(id="content").text.strip()
            collection_date = datetime.strptime(date_text, "%A, %d/%m/%Y")

            bin_types = bin_section.find(id="main1").findAll("li")
            for bin_type in bin_types:
                bin_type_name = bin_type.text.split("(")[0].strip()

                data["bins"].append(
                    {
                        "type": bin_type_name,
                        "collectionDate": collection_date.strftime(date_format),
                    }
                )

        return data
