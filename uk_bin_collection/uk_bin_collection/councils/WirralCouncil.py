import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_postcode = kwargs.get("postcode")
        user_uprn = kwargs.get("uprn")
        check_postcode(user_postcode)

        base = "https://www.wirral.gov.uk"
        url = f"{base}/bins-and-recycling/bin-collection-dates"

        s = requests.Session()
        s.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            }
        )

        # Step 1: GET form to obtain form_build_id
        r1 = s.get(url, verify=False)
        r1.raise_for_status()
        soup1 = BeautifulSoup(r1.text, "html.parser")

        form = soup1.find("form", id="localgov-waste-collection-postcode-form")
        if not form:
            raise ValueError("Postcode form not found on page")

        data1 = {}
        for inp in form.find_all("input"):
            name = inp.get("name")
            if name:
                data1[name] = inp.get("value", "")
        data1["postcode"] = user_postcode

        # Step 2: POST postcode to get address list
        r2 = s.post(url, data=data1, verify=False)
        r2.raise_for_status()
        soup2 = BeautifulSoup(r2.text, "html.parser")

        form2 = soup2.find("form", id="localgov-waste-collection-address-select-form")
        if not form2:
            raise ValueError(f"No addresses found for postcode {user_postcode}")

        # If UPRN provided, use it directly; otherwise pick first address
        select = form2.find("select", id="edit-uprn")
        if not select:
            raise ValueError("Address dropdown not found")

        options = select.find_all("option")
        valid_options = [o for o in options if o.get("value")]

        if not valid_options:
            raise ValueError(f"No addresses returned for {user_postcode}")

        selected_uprn = None
        if user_uprn:
            for o in valid_options:
                if str(o["value"]) == str(user_uprn):
                    selected_uprn = o["value"]
                    break
            if not selected_uprn:
                raise ValueError(
                    f"UPRN {user_uprn} not found in address list for {user_postcode}"
                )
        else:
            selected_uprn = valid_options[0]["value"]

        # Step 3: POST UPRN selection
        action = form2.get("action", "")
        post_url = f"{base}{action}" if action.startswith("/") else action

        data2 = {}
        for inp in form2.find_all("input"):
            name = inp.get("name")
            if name:
                data2[name] = inp.get("value", "")
        data2["uprn"] = selected_uprn

        r3 = s.post(post_url, data=data2, verify=False)
        r3.raise_for_status()
        soup3 = BeautifulSoup(r3.text, "html.parser")

        # Parse collection dates from calendar
        data = {"bins": []}
        current_year = datetime.now().year

        # Each month has an h3 heading, followed by day entries
        # Day entries contain: day number, bin type, and bin colour
        month_sections = soup3.find_all("h3")
        for month_h3 in month_sections:
            month_name = month_h3.text.strip()
            if not re.match(
                r"^(January|February|March|April|May|June|July|August|September|October|November|December)$",
                month_name,
            ):
                continue

            container = month_h3.find_parent("div")
            if not container:
                continue

            # Find day entries - each has a day number and collection info
            day_items = container.find_all(
                "div", class_=re.compile(r"localgov-waste-collection-day")
            )

            if not day_items:
                # Fallback: parse text content
                text = container.get_text(separator="\n", strip=True)
                lines = text.split("\n")
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    if line.isdigit():
                        day = int(line)
                        # Next lines should be bin type info
                        bin_types = []
                        i += 1
                        while i < len(lines) and not lines[i].strip().isdigit():
                            bin_line = lines[i].strip()
                            if bin_line and bin_line != month_name:
                                bin_types.append(bin_line)
                            i += 1
                        # Group consecutive non-digit lines as bin type entries
                        # Pattern: "Bin type\nColour" pairs
                        j = 0
                        while j < len(bin_types):
                            bin_type = bin_types[j]
                            if bin_type in (
                                "Green",
                                "Grey",
                                "Brown",
                                "Blue",
                                "Black",
                            ):
                                j += 1
                                continue
                            try:
                                collection_date = datetime(
                                    current_year,
                                    datetime.strptime(month_name, "%B").month,
                                    day,
                                )
                                data["bins"].append(
                                    {
                                        "type": bin_type,
                                        "collectionDate": collection_date.strftime(
                                            date_format
                                        ),
                                    }
                                )
                            except ValueError:
                                pass
                            j += 1
                    else:
                        i += 1

        if not data["bins"]:
            # Fallback: try "Next collection" section
            next_h2 = soup3.find("h2", string=re.compile(r"Next collection"))
            if next_h2:
                parent = next_h2.find_parent("div")
                if parent:
                    text = parent.get_text(separator="\n", strip=True)
                    # Parse "Friday 15 May\nNon-recyclable waste" pattern
                    date_match = re.search(
                        r"(\w+day)\s+(\d{1,2})\s+(\w+)", text
                    )
                    if date_match:
                        day = int(date_match.group(2))
                        month = date_match.group(3)
                        try:
                            collection_date = datetime.strptime(
                                f"{day} {month} {current_year}", "%d %B %Y"
                            )
                            # Find bin type after the date
                            type_match = re.search(
                                r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+\d{1,2}\s+\w+\n(.+)",
                                text,
                            )
                            if type_match:
                                bin_type = type_match.group(1).strip()
                                data["bins"].append(
                                    {
                                        "type": bin_type,
                                        "collectionDate": collection_date.strftime(
                                            date_format
                                        ),
                                    }
                                )
                        except ValueError:
                            pass

        if not data["bins"]:
            raise ValueError("No collection data found on page")

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
