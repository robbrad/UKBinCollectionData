from typing import Dict, Any, Optional
from bs4 import BeautifulSoup, Tag, NavigableString
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

"""
This module provides bin collection data for Cheshire East Council.
"""

class CouncilClass(AbstractGetBinDataClass):
    """
    A class to fetch and parse bin collection data for Cheshire East Council.
    """

    def parse_data(self, page: Any, **kwargs: Any) -> Dict[str, Any]:
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
