from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        check_uprn(user_uprn)
        check_postcode(user_postcode)
        bindata = {"bins": []}

        API_URL = "https://www.broxbourne.gov.uk/xfp/form/205"

        post_data = {
            "page": "490",
            "locale": "en_GB",
            "qacf7e570cf99fae4cb3a2e14d5a75fd0d6561058_0_0": user_postcode,
            "qacf7e570cf99fae4cb3a2e14d5a75fd0d6561058_1_0": user_uprn,
            "next": "Next",
        }

        r = requests.post(API_URL, data=post_data)
        r.raise_for_status()

        soup = BeautifulSoup(r.content, features="html.parser")
        soup.prettify()

        form__instructions = soup.find(attrs={"class": "form__instructions"})
        table = form__instructions.find("table")

        rows = table.find_all("tr")

        current_year = datetime.now().year
        current_month = datetime.now().month 

        # Process each row into a list of dictionaries
        for row in rows[1:]:  # Skip the header row
            columns = row.find_all("td")
            collection_date_text = (
                columns[0].get_text(separator=" ").replace("\xa0", " ").strip()
            )
            service = columns[1].get_text(separator=" ").replace("\xa0", " ").strip()

            # Safely try to parse collection date
            if collection_date_text:
                try:
                    collection_date = datetime.strptime(collection_date_text, "%a %d %b")
                    if collection_date.month == 1 and current_month != 1:
                        collection_date = collection_date.replace(year=current_year + 1)
                    else:
                        collection_date = collection_date.replace(year=current_year)

                    formatted_collection_date = collection_date.strftime("%d/%m/%Y")  # Use your desired date format
                    dict_data = {
                        "type": service,
                        "collectionDate": formatted_collection_date,
                    }
                    bindata["bins"].append(dict_data)
                except ValueError:
                    # Skip invalid collection_date
                    continue

        # Sort valid bins by collectionDate
        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )
        return bindata
