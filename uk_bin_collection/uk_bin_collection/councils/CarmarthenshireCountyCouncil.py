import re

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# The council's "check your recycling day" page. It lists every container a
# property has, for both the old blue-bag service and the separated recycling
# service that started on 2 November 2026.
RECYCLING_INFO_URL = (
    "https://www.carmarthenshire.gov.wales/umbraco/Surface/"
    "SurfaceKerbsiteRecyclingChecker/GetRecyclingInfo/"
)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
}
DATE_PATTERN = re.compile(r"^\d{2}/\d{2}/\d{4}$")


def _clean(text: str) -> str:
    return " ".join(text.split())


def _container_name(container, date_paragraph) -> str:
    # Kerbside containers name themselves on the first line of the paragraph
    # ("Blue bags", "Food waste bin", "Black box", ...). The garden and
    # hygiene/nappy blocks start straight with the date, so their name is the
    # heading of the section they sit in.
    for text in date_paragraph.find_all(string=True):
        if text.strip():
            if text.find_parent("strong") is None:
                return _clean(text)
            break
    heading = container.find_previous("h2")
    return _clean(heading.get_text()) if heading else ""


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

        response = requests.get(
            RECYCLING_INFO_URL,
            params={"uprn": user_uprn, "lang": "en-GB"},
            headers=HEADERS,
            timeout=30,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        for container in soup.select(".recycling-outer-container"):
            date_tag = next(
                (
                    strong
                    for strong in container.find_all("strong")
                    if DATE_PATTERN.match(strong.get_text(strip=True))
                ),
                None,
            )
            if date_tag is None:
                continue

            paragraph = date_tag.find_parent("p") or container
            bin_type = _container_name(container, paragraph)
            if not bin_type:
                continue

            collection_date = datetime.strptime(
                date_tag.get_text(strip=True), "%d/%m/%Y"
            ).strftime(date_format)

            bindata["bins"].append(
                {
                    "type": bin_type,
                    "collectionDate": collection_date,
                }
            )

        if not bindata["bins"]:
            raise ValueError(
                f"Carmarthenshire returned no collections for UPRN {user_uprn}"
            )

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
