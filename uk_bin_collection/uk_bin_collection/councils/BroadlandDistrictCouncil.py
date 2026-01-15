# This script pulls (in one hit) the data from Broadland District Council Bins Data

import json
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse
from urllib.parse import quote

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):

    def parse_data(self, page: str = None, **kwargs) -> dict:
        try:
            data = {"bins": []}

            uprn = kwargs.get("uprn")
            postcode = kwargs.get("postcode")
            url = kwargs.get("url")

            check_uprn(uprn)
            check_postcode(postcode)
            uprn = str(uprn).zfill(12)

            cookie_json = json.dumps(
                {
                    "Uprn": uprn,
                    "Address": postcode,
                },
                separators=(",", ":")
            )
            cookie_value = quote(cookie_json, safe="")

            headers = {
                "Cookie": f"MyArea.Data={cookie_value}",
                "User-Agent": "curl/8.5.0",  # optional but helps match working curl
                "Accept": "*/*",
            }

            r = requests.get(
                "https://area.southnorfolkandbroadland.gov.uk/",
                headers=headers,
                timeout=30
            )
            
            
            r.raise_for_status()

            
            soup = BeautifulSoup(r.text, "html.parser")

            # Initialize current date
            current_date = datetime.now()

            # Process collection details
            print("Looking for collection details in the page...")

            # Find the card-body div that contains the bin collection information
            card_body = soup.find("div", class_="card-body")
            if card_body:


                # Find the "Your next collections" heading
                next_collections_heading = card_body.find(
                    "h4", string="Your next collections"
                )

                if next_collections_heading:
                    # Find all bin collection divs (each with class "my-2")
                    bin_divs = next_collections_heading.find_next_siblings(
                        "div", class_="my-2"
                    )

                    print(f"Found {len(bin_divs)} bin collection divs")

                    for bin_div in bin_divs:
                        # Find the bin type (in a strong tag)
                        bin_type_elem = bin_div.find("strong")
                        bin_type = None

                        if bin_type_elem:
                            bin_type = bin_type_elem.text.strip().replace(
                                " (if applicable)", ""
                            )

                            # Get the parent element that contains both the bin type and date
                            text_container = bin_type_elem.parent
                            if text_container:
                                # Extract the full text and remove the bin type to get the date part
                                full_text = text_container.get_text(strip=True)
                                date_text = full_text.replace(bin_type, "").strip()
                                print(f"Unparsed collection date: {date_text}")

                                # Parse the date
                                # First, remove any ordinal indicators (1st, 2nd, 3rd, etc.)
                                cleaned_date_text = (
                                    remove_ordinal_indicator_from_date_string(date_text)
                                )

                                from dateutil.parser import parse

                                parsed_date = parse(cleaned_date_text, fuzzy=True)
                                bin_date = parsed_date.strftime("%d/%m/%Y")

                                # Only process if we have both bin_type and bin_date
                                if bin_type and bin_date:
                                    dict_data = {
                                        "type": bin_type,
                                        "collectionDate": bin_date,
                                    }
                                    data["bins"].append(dict_data)
                                    print(f"Added bin data: {dict_data}")
        except Exception as e:
            print(f"An error occurred: {e}")
            raise


        return data
