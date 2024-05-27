from bs4 import BeautifulSoup
from datetime import datetime
import re
from uk_bin_collection.uk_bin_collection.common import *  # Consider specific imports
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        soup = BeautifulSoup(page.text, "html.parser")

        bins_data = {"bins": []}
        bin_collections = []

        results_wrapper = soup.find("div", {"class": "results-table-wrapper"})
        if not results_wrapper:
            return bins_data  # Return empty if the results wrapper is not found

        bins = results_wrapper.find_all("div", {"class": "service-wrapper"})
        for bin_item in bins:
            service_name = bin_item.find("h3", {"class": "service-name"})
            next_service = bin_item.find("td", {"class": "next-service"})

            if service_name and next_service:
                bin_type = service_name.get_text().replace("Collection", "bin").strip()
                date_span = next_service.find("span", {"class": "table-label"})
                date_text = (
                    date_span.next_sibling.get_text().strip() if date_span else None
                )

                if date_text and re.match(r"\d{2}/\d{2}/\d{4}", date_text):
                    try:
                        bin_date = datetime.strptime(date_text, "%d/%m/%Y")
                        bin_collections.append((bin_type, bin_date))
                    except ValueError:
                        continue

        for bin_type, bin_date in sorted(bin_collections, key=lambda x: x[1]):
            bins_data["bins"].append(
                {
                    "type": bin_type.capitalize(),
                    "collectionDate": bin_date.strftime("%d/%m/%Y"),
                }
            )

        return bins_data
