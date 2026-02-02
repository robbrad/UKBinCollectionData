import requests
from datetime import datetime
from uk_bin_collection.uk_bin_collection.common import date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete class for Gosport Borough Council bin collection data.
    Uses the Supatrak API to fetch collection schedules by postcode.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        """
        Fetch bin collection data for Gosport Borough Council using postcode.

        Args:
            page (str): Unused parameter (kept for interface compatibility).
            postcode (str, in kwargs): Postcode to search for collection data.

        Returns:
            dict: Dictionary containing bin collection data with structure:
                {
                    "bins": [
                        {
                            "type": str,  # Bin type (e.g., "DOMESTIC", "RECYCLING", "GARDEN")
                            "collectionDate": str  # Date in standard format
                        },
                        ...
                    ]
                }

        Raises:
            ValueError: If postcode is not provided or API request fails.
        """
        postcode = kwargs.get("postcode")
        if not postcode:
            raise ValueError("Postcode is required for Gosport Borough Council")

        # API endpoint from the council's website JavaScript
        api_url = "https://api.supatrak.com/API/JobTrak/NextCollection"
        
        # Headers from the council's website
        headers = {
            "Authorization": "Basic VTAwMDE4XEFQSTpUcjRja2luZzEh",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        params = {"postcode": postcode}

        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to fetch bin collection data: {e}")

        if not data or len(data) == 0:
            raise ValueError(f"No collection data found for postcode: {postcode}")

        bins = []
        seen = set()  # Track unique type+date combinations
        
        for collection in data:
            waste_type = collection.get("WasteType", "Unknown")
            next_collection = collection.get("NextCollection")
            
            if next_collection:
                # Parse the date string (format: "2025-02-05T00:00:00")
                collection_date = datetime.fromisoformat(next_collection.replace("Z", "+00:00"))
                formatted_date = collection_date.strftime(date_format)
                
                # Create unique key to avoid duplicates
                unique_key = (waste_type, formatted_date)
                if unique_key not in seen:
                    seen.add(unique_key)
                    bins.append({
                        "type": waste_type,
                        "collectionDate": formatted_date
                    })

        return {"bins": bins}
