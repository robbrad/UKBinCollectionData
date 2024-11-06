from time import sleep

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
        # check_uprn(user_uprn)
        bindata = {"bins": []}

        URI = f"https://waste-services.sutton.gov.uk/waste/{user_uprn}"

        s = requests.Session()

        r = s.get(URI)
        while "Loading your bin days..." in r.text:
            sleep(2)
            r = s.get(URI)
        r.raise_for_status()

        soup = BeautifulSoup(r.content, "html.parser")

        current_year = datetime.now().year
        next_year = current_year + 1

        services = soup.find_all("h3", class_="govuk-heading-m waste-service-name")

        for service in services:
            bin_type = service.get_text(
                strip=True
            )  # Bin type name (e.g., 'Food waste', 'Mixed recycling')
            if bin_type == "Bulky waste":
                continue
            service_details = service.find_next("div", class_="govuk-grid-row")

            next_collection = (
                service_details.find("dt", string="Next collection")
                .find_next_sibling("dd")
                .get_text(strip=True)
            )

            next_collection = datetime.strptime(
                remove_ordinal_indicator_from_date_string(next_collection),
                "%A, %d %B",
            )

            if next_collection.month == 1:
                next_collection = next_collection.replace(year=next_year)
            else:
                next_collection = next_collection.replace(year=current_year)

            dict_data = {
                "type": bin_type,
                "collectionDate": next_collection.strftime("%d/%m/%Y"),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
