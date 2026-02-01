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
        
        # Try new dataset first (2025on), fall back to old dataset if no data found
        # Council is migrating data between datasets, not all postcodes migrated yet
        datasets = ["DomesticBinCollections2025on", "DomesticBinCollections"]
        bin_data = None
        
        for dataset in datasets:
            params = {
                "type": "JSON",
                "list": dataset,
                "Road or Postcode": user_postcode,
            }

            response = requests.get(
                "https://www.fareham.gov.uk/internetlookups/search_data.aspx",
                params=params,
                headers=headers,
            )

            response_data = response.json()["data"]
            
            # Check if we got actual data (not just an error message)
            if isinstance(response_data, dict) and "rows" in response_data:
                bin_data = response_data
                break
        
        data = {"bins": []}

        if bin_data and "rows" in bin_data:
            row = bin_data["rows"][0]
            
            # New dataset format: "BinCollectionInformation" field
            if "BinCollectionInformation" in row:
                collection_str = row["BinCollectionInformation"]
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
                    raise RuntimeError("Dates not parsed correctly from new dataset format.")
            
            # Old dataset format: "DomesticBinDay" field
            elif "DomesticBinDay" in row:
                collection_str = row["DomesticBinDay"]
                # Parse dates from format like "Friday - Collections are 06/02/2026 (Refuse) and 13/02/2026 (Recycling)"
                results = re.findall(r'(\d{1,2}/\d{1,2}/\d{4})\s*\(([^)]+)\)', collection_str)
                
                if results:
                    for result in results:
                        collection_date = datetime.strptime(result[0], "%d/%m/%Y")
                        dict_data = {
                            "type": result[1],
                            "collectionDate": collection_date.strftime(date_format),
                        }
                        data["bins"].append(dict_data)
                else:
                    raise RuntimeError("Dates not parsed correctly from old dataset format.")

            # Look for garden waste key (works for both formats)
            for key, value in row.items():
                if key.startswith("GardenWasteBinDay") or key == "GardenWasteDay":
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
