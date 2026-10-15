import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# The council's site is fronted by an Azure Application Gateway that 403s the
# default python-requests User-Agent - identify the scraper honestly instead.
_HEADERS = {"User-Agent": get_scraper_user_agent()}

# The old /repositories/hidden-pages/bin-finder page now 404s. The site's own
# address lookup (scripts/TDC/autocomplete.js) loads results from this Umbraco
# surface controller instead, which returns the same collection-card fragment.
API_URL = "https://www.teignbridge.gov.uk/umbraco/surface/bincollection/GetCollections"


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

        response = requests.get(
            API_URL, params={"uprn": user_uprn}, headers=_HEADERS, timeout=30
        )
        if response.status_code == 403:
            raise ConnectionError(
                "Teignbridge's website returned 403 Forbidden - its Azure "
                "Application Gateway is blocking this client, not rejecting "
                "the UPRN."
            )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, features="html.parser")

        # Each collection day is an <h3 class="binCollectionH3"> holding the
        # date and weekday, followed by a container of that day's bin types.
        collection_dates = soup.find_all("h3", class_="binCollectionH3")
        bin_type_containers = soup.find_all("div", {"class": "binInfoContainer"})

        if not collection_dates:
            raise ValueError(
                f"Teignbridge returned no collection days for UPRN {user_uprn}. "
                f"Check the UPRN is a current Teignbridge household address."
            )

        for date_heading, container in zip(collection_dates, bin_type_containers):
            # e.g. "15 October 2026Thursday" - the weekday is a nested span
            # with no separator, which "%d %B %Y%A" consumes directly.
            collection_date = date_heading.get_text(strip=True)
            parsed_date = datetime.strptime(collection_date, "%d %B %Y%A")

            for bin_type in container.find_all("div", {"class": "binInfoLine"}):
                bindata["bins"].append(
                    {
                        "type": bin_type.get_text(strip=True),
                        "collectionDate": parsed_date.strftime(date_format),
                    }
                )

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )
        return bindata
