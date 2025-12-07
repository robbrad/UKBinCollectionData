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
        """
        Retrieve and parse Fareham bin collection dates for a given postcode into a structured dictionary.
        
        Parameters:
            page (str): Source page content (not used; present for interface compatibility).
            postcode (str, via kwargs['postcode']): Postcode to query; must be a valid postcode.
        
        Returns:
            dict: A dictionary with a "bins" key containing a list of entries. Each entry is a dict with:
                - "type" (str): The bin type (e.g., "Recycling", "Garden").
                - "collectionDate" (str): Collection date formatted as "DD/MM/YYYY".
        
        Raises:
            ValueError: If the postcode is not found on the website.
            RuntimeError: If expected collection dates cannot be parsed from the response.
        """
        user_postcode = kwargs.get("postcode")
        check_postcode(user_postcode)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
        }
        params = {
            "type": "JSON",
            "list": "DomesticBinCollections2025on",
            "Road": "",
            "Postcode": user_postcode,
        }

        response = requests.get(
            "https://www.fareham.gov.uk/internetlookups/search_data.aspx",
            params=params,
            headers=headers,
        )

        bin_data = response.json()["data"]
        data = {"bins": []}

        if "rows" in bin_data:
            collection_str = bin_data["rows"][0]["BinCollectionInformation"]

            results = re.findall(r'(\d{1,2}/\d{1,2}/\d{4}|today)\s*\(([^)]+)\)', collection_str)

            if results:
                for result in results:
                    if (result[0] == "today"):
                        collection_date = datetime.today()
                    else:
                        collection_date = datetime.strptime(result[0], "%d/%m/%Y")
                    dict_data = {
                        "type": result[1],
                        "collectionDate": collection_date.strftime(date_format),
                    }
                    data["bins"].append(dict_data)
            else:
                raise RuntimeError("Dates not parsed correctly.")

            # Look for garden waste key
            for key, value in bin_data["rows"][0].items():
                if key.startswith("GardenWasteBinDay"):
                    results = re.findall(r'(\d{1,2}/\d{1,2}/\d{4})', value)
                    if not results:
                        continue
                    collection_date = datetime.strptime(results[0], "%d/%m/%Y")
                    garden_data = {
                        "type": "Garden",
                        "collectionDate": collection_date.strftime(date_format),
                    }
                    data["bins"].append(garden_data)

        else:
            raise ValueError("Postcode not found on website.")

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return data