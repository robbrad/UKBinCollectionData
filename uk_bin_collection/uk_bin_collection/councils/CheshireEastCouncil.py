from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

#Cheshire East
class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        soup = BeautifulSoup(page.text, features="html.parser")

        bin_data_dict = {"bins": []}

        table = soup.find("table", {"class": "job-details"})
        if table:
            rows = table.find_all("tr", {"class": "data-row"})

            for row in rows:
                cells = row.find_all(
                    "td", {"class": lambda L: L and L.startswith("visible-cell")}
                )
                labels = cells[0].find_all("label") if cells else []

                if len(labels) >= 3:
                    bin_type = labels[2].get_text(strip=True)
                    collection_date = labels[1].get_text(strip=True)

                    bin_data_dict["bins"].append(
                        {
                            "type": bin_type,
                            "collectionDate": collection_date,
                        }
                    )
        return bin_data_dict
