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
        data = {"bins": []}
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)
        check_paon(user_paon)

        URI = "https://recyclingservices.brent.gov.uk/waste"

        payload = {"postcode": user_postcode}

        s = requests.Session()

        # Make the POST request
        response = s.post(URI, data=payload)

        # Make a BS4 object
        soup = BeautifulSoup(response.content, features="html.parser")

        address_list = soup.find_all("option")

        current_year = datetime.now().year
        next_year = current_year + 1

        for address in address_list:
            if user_paon in (address.text):
                address_id = address.get("value")
                URI = f"https://recyclingservices.brent.gov.uk/waste/{address_id}"

                counter = 0
                r = s.get(URI)
                while "Loading your bin days..." in r.text:
                    counter = counter + 1
                    if counter == 20:
                        return data
                    sleep(2)
                    r = s.get(URI)

                r.raise_for_status()

                soup = BeautifulSoup(r.content, features="html.parser")

                wastecollections = soup.find("div", {"class": "waste__collections"})

                # Find all waste service sections
                waste_services = wastecollections.find_all(
                    "h3", class_="govuk-heading-m waste-service-name"
                )

                for service in waste_services:
                    # Get the collection type (e.g., Rubbish, Recycling)
                    collection_type = (service.get_text(strip=True)).split("\n")[0]

                    # Find the sibling container holding details
                    service_details = service.find_next(
                        "dl", class_="govuk-summary-list"
                    )

                    if service_details:
                        # Extract next collection date only
                        next_collection_row = service_details.find(
                            "dt", string="Next collection"
                        )
                        if next_collection_row:
                            next_collection = next_collection_row.find_next_sibling(
                                "dd"
                            ).get_text(strip=True)

                            # Remove the adjusted collection time message
                            if (
                                "(this collection has been adjusted from its usual time)"
                                in next_collection
                            ):
                                next_collection = next_collection.replace(
                                    "(this collection has been adjusted from its usual time)",
                                    "",
                                ).strip()

                            # Parse date from format like "Wednesday, 7th May"
                            next_collection = remove_ordinal_indicator_from_date_string(
                                next_collection
                            )
                            try:
                                next_collection_date = datetime.strptime(
                                    next_collection, "%A, %d %B"
                                )

                                # Handle year rollover
                                if (
                                    datetime.now().month == 12
                                    and next_collection_date.month == 1
                                ):
                                    next_collection_date = next_collection_date.replace(
                                        year=next_year
                                    )
                                else:
                                    next_collection_date = next_collection_date.replace(
                                        year=current_year
                                    )

                                dict_data = {
                                    "type": collection_type.strip(),
                                    "collectionDate": next_collection_date.strftime(
                                        date_format
                                    ),
                                }
                                data["bins"].append(dict_data)
                                print(dict_data)
                            except ValueError as e:
                                print(f"Error parsing date {next_collection}: {e}")

        return data
