import json

import requests
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_postcode = kwargs.get("postcode")
        check_postcode(user_postcode)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
        }
        params = {
            "type": "JSON",
            "list": "DomesticBinCollections",
            "Road": "",
            "Postcode": user_postcode
        }

        response = requests.get(
            "https://www.fareham.gov.uk/internetlookups/search_data.aspx",
            params  = params,
            headers = headers
        )

        bin_data = response.json()["data"]
        data = {"bins": []}

        if "rows" in bin_data:
            collection_str = bin_data["rows"][0]["DomesticBinDay"]
            
            results = re.findall(r"(\d\d?\/\d\d?\/\d{4}) \((\w*)\)", collection_str)

            if results:
                    for result in results:
                        collection_date = datetime.strptime(result[0], "%d/%m/%Y")
                        dict_data = {
                            "type": result[1],
                            "collectionDate": collection_date.strftime(date_format),
                        }
                        data["bins"].append(dict_data)

                        # Garden waste is also collected on recycling day
                        if (dict_data["type"] == "Recycling"):
                            garden_data = {
                                "type": "Garden",
                                "collectionDate": dict_data["collectionDate"],
                            }
                            data["bins"].append(garden_data)
            else:
                raise RuntimeError("Dates not parsed correctly.")
        else:
            raise ValueError("Postcode not found on website.")

        data["bins"].sort(
            key=lambda x: datetime.strptime(
            x.get("collectionDate"), "%d/%m/%Y"
            )
        )

        return data
