import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# Conwy's classic-ASP "check my collection day" lookup serves its result page
# from a path that rotates each year (observed: collection-result-soap-xmas2025
# then -xmas2026, unsuffixed collection-result-soap.asp hangs indefinitely).
# Each rotation silently breaks scrapers hardcoded to the prior suffix. Try
# the current year first, then adjacent years, then the unsuffixed path as
# a last resort.
_RESULT_URL_TEMPLATE = (
    "https://www.conwy.gov.uk/Contensis-Forms/erf/collection-result-soap-xmas{year}.asp"
    "?ilangid=1&uprn={uprn}"
)
_RESULT_URL_UNSUFFIXED = (
    "https://www.conwy.gov.uk/Contensis-Forms/erf/collection-result-soap.asp"
    "?ilangid=1&uprn={uprn}"
)


def _candidate_urls(uprn):
    year = datetime.now().year
    yield _RESULT_URL_TEMPLATE.format(year=year, uprn=uprn)
    yield _RESULT_URL_TEMPLATE.format(year=year + 1, uprn=uprn)
    yield _RESULT_URL_TEMPLATE.format(year=year - 1, uprn=uprn)
    yield _RESULT_URL_UNSUFFIXED.format(uprn=uprn)


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
        }

        last_err = None
        html = None
        for url in _candidate_urls(user_uprn):
            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                if "containererf" in response.text:
                    html = response.text
                    break
            except requests.exceptions.RequestException as e:
                last_err = e
                time.sleep(1)

        if html is None:
            if last_err is not None:
                raise last_err
            raise Exception("Conwy returned no valid response on any candidate URL")

        soup = BeautifulSoup(html, features="html.parser")
        data = {"bins": []}

        for bin_section in soup.select('div[class*="containererf"]'):
            date_node = bin_section.find(id="content")
            bins_node = bin_section.find(id="main1")
            if not date_node or not bins_node:
                continue
            try:
                collection_date = datetime.strptime(
                    date_node.get_text(strip=True), "%A, %d/%m/%Y"
                )
            except ValueError:
                continue
            for bin_type in bins_node.find_all("li"):
                bin_type_name = bin_type.get_text(strip=True).split("(")[0].strip()
                if not bin_type_name:
                    continue
                data["bins"].append({
                    "type": bin_type_name,
                    "collectionDate": collection_date.strftime(date_format),
                })

        return data
