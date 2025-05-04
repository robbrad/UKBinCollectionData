from typing import Any, Dict, Optional

from bs4 import BeautifulSoup, NavigableString, Tag

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

"""
This module provides bin collection data for Cheshire East Council.
"""


class CouncilClass(AbstractGetBinDataClass):
    """
    A class to fetch and parse bin collection data for Cheshire East Council.
    """

    def parse_data(self, page: Any, **kwargs: Any) -> Dict[str, Any]:

        try:
            user_uprn = kwargs.get("uprn")
            url = f"https://online.cheshireeast.gov.uk/MyCollectionDay/SearchByAjax/GetBartecJobList?uprn={user_uprn}"
            if not user_uprn:
                # This is a fallback user stored a URL in old system. Ensures backwards compatibility.
                url = kwargs.get("url")
        except Exception as e:
            raise ValueError(f"Error getting identifier: {str(e)}")

        # Add warning suppression for the insecure request
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Make request with SSL verification disabled
        page = requests.get(url, verify=False)

        soup = BeautifulSoup(page.text, features="html.parser")

        bin_data_dict: Dict[str, Any] = {"bins": []}

        table: Optional[Tag | NavigableString] = soup.find(
            "table", {"class": "job-details"}
        )

        if isinstance(table, Tag):  # Ensure we only proceed if 'table' is a Tag
            rows = table.find_all("tr", {"class": "data-row"})

            for row in rows:
                cells = row.find_all(
                    "td",
                    {
                        "class": lambda L: isinstance(L, str)
                        and L.startswith("visible-cell")
                    },  # Explicitly check if L is a string
                )
                labels: list[Tag] = cells[0].find_all("label") if cells else []

                if len(labels) >= 3:
                    bin_type: str = labels[2].get_text(strip=True)
                    collection_date: str = labels[1].get_text(strip=True)

                    bin_data_dict["bins"].append(
                        {
                            "type": bin_type,
                            "collectionDate": collection_date,
                        }
                    )

        return bin_data_dict
