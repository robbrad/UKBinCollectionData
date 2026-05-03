import re

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
        user_paon = kwargs.get("paon")

        bindata = {"bins": []}
        results_html = None

        # Prefer postcode+house_number lookup (works for all UPRNs)
        if user_postcode and user_paon:
            response = requests.get(
                "https://exeter.gov.uk/repositories/hidden-pages/address-finder/",
                params={"qsource": "POSTCODE", "qtype": "bins", "term": user_postcode},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            if data:
                # Extract leading number from paon for matching
                paon_num = re.match(r"^(\d+)", str(user_paon).strip())
                paon_prefix = paon_num.group(1) if paon_num else str(user_paon).strip()

                for entry in data:
                    label = entry.get("label", "")
                    if label.strip().startswith(paon_prefix):
                        results_html = entry.get("Results")
                        break

                # Fallback: first entry if no match
                if not results_html and data:
                    results_html = data[0].get("Results")

        # Fall back to UPRN lookup (original method)
        if not results_html and user_uprn:
            check_uprn(user_uprn)
            response = requests.get(
                f"https://exeter.gov.uk/repositories/hidden-pages/address-finder/?qsource=UPRN&qtype=bins&term={user_uprn}",
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            if data:
                results_html = data[0].get("Results")

        if not results_html:
            return bindata

        soup = BeautifulSoup(results_html, "html.parser")

        for section in soup.find_all("h2"):
            bin_type = section.text.strip()
            h3 = section.find_next("h3")
            if not h3:
                continue
            collection_date = h3.text.strip()

            dict_data = {
                "type": bin_type,
                "collectionDate": datetime.strptime(
                    remove_ordinal_indicator_from_date_string(collection_date),
                    "%A, %d %B %Y",
                ).strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
