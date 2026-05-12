import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_postcode = kwargs.get("postcode")
        check_postcode(user_postcode)

        root_url = "https://myproperty.molevalley.gov.uk/molevalley/api/live_addresses/{}?format=json".format(
            user_postcode
        )
        response = requests.get(root_url, verify=False)

        if not response.ok:
            raise ValueError("Invalid server response code retrieving data.")

        json_data = response.json()

        if len(json_data["results"]["features"]) == 0:
            raise ValueError("No collection data found for postcode provided.")

        properties_found = json_data["results"]["features"]

        html_data = None
        uprn = kwargs.get("uprn")
        if uprn:
            check_uprn(uprn)
            for item in properties_found:
                if uprn == str(int(item["properties"]["blpu_uprn"])):
                    html_data = item["properties"]["three_column_layout_html"]
                    break
            if html_data is None:
                raise ValueError("No collection data found for UPRN provided.")
        else:
            html_data = properties_found[0]["properties"]["three_column_layout_html"]

        if "<!--" in html_data and "-->" in html_data:
            html_data = html_data.replace("<!--", "").replace("-->", "")

        soup = BeautifulSoup(html_data, "html.parser")

        data = {"bins": []}
        regex_date = re.compile(r"(\d{2}/\d{2}/\d{4})")

        bins_panel = soup.find("h2", string="Bins and Recycling")
        if not bins_panel:
            raise ValueError(
                "Unable to find 'Bins and Recycling' panel in the HTML data."
            )

        panel = bins_panel.find_parent("div", class_="panel")

        for strong_tag in panel.find_all("strong"):
            if strong_tag.parent != panel:
                continue

            bin_type = strong_tag.text.strip()
            next_p = strong_tag.find_next_sibling("p")
            if not next_p:
                continue

            collection_text = next_p.get_text()
            match = regex_date.search(collection_text)
            if match:
                collection_date = datetime.strptime(
                    match.group(1), "%d/%m/%Y"
                ).date()
                data["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": collection_date.strftime("%d/%m/%Y"),
                    }
                )

        regex_additional = re.compile(r"We also collect (.*?) on (.*?) -")
        for p in panel.find_all("p"):
            additional_match = regex_additional.match(p.get_text().strip())
            if (
                additional_match
                and "each collection day" in additional_match.group(2)
                and data["bins"]
            ):
                earliest = min(
                    datetime.strptime(b["collectionDate"], "%d/%m/%Y")
                    for b in data["bins"]
                )
                data["bins"].append(
                    {
                        "type": additional_match.group(1),
                        "collectionDate": earliest.strftime("%d/%m/%Y"),
                    }
                )

        if not data["bins"]:
            raise ValueError("No valid collection dates were found in the data.")

        return data
