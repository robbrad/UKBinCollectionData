import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
from time import sleep

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

def remove_ordinal_indicator_from_date_string(date_str):
    return re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)

class CouncilClass(AbstractGetBinDataClass):

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        bindata = {"bins": []}

        URI = f"https://waste-services.sutton.gov.uk/waste/{user_uprn}"

        s = requests.Session()
        r = s.get(URI)
        while "Loading your bin days..." in r.text:
            sleep(2)
            r = s.get(URI)
        r.raise_for_status()

        soup = BeautifulSoup(r.content, "html.parser")
        current_year = datetime.now().year
        next_year = current_year + 1

        # Find all h3 headers (bin types)
        services = soup.find_all("h3")
        for service in services:
            bin_type = service.get_text(strip=True)
            if "Bulky Waste" in bin_type:
                continue

            # Find the next element (next sibling) which is likely a paragraph with date info
            next_sib = service.find_next_sibling()
            while next_sib and getattr(next_sib, 'name', None) not in [None, 'p']:
                next_sib = next_sib.find_next_sibling()

            next_coll = None
            if next_sib:
                text = next_sib.get_text() if hasattr(next_sib, 'get_text') else str(next_sib)
                match = re.search(r"Next collection\s*([A-Za-z]+,? \d{1,2}(?:st|nd|rd|th)? [A-Za-z]+)", text)
                if match:
                    next_coll = match.group(1)
                else:
                    # Sometimes the text may be attached without a space after 'Next collection'
                    match = re.search(r"Next collection([A-Za-z]+,? \d{1,2}(?:st|nd|rd|th)? [A-Za-z]+)", text)
                    if match:
                        next_coll = match.group(1)

            # Try several siblings forward if not found
            if not next_coll:
                sib_try = service
                for _ in range(3):
                    if sib_try:
                        sib_try = sib_try.find_next_sibling()
                    else:
                        break
                    if sib_try:
                        text = sib_try.get_text() if hasattr(sib_try, 'get_text') else str(sib_try)
                        match = re.search(r"Next collection\s*([A-Za-z]+,? \d{1,2}(?:st|nd|rd|th)? [A-Za-z]+)", text)
                        if match:
                            next_coll = match.group(1)
                            break

            if next_coll:
                next_coll = remove_ordinal_indicator_from_date_string(next_coll)
                try:
                    next_collection = datetime.strptime(next_coll, "%A, %d %B")
                except ValueError:
                    continue

                if (datetime.now().month == 12 and next_collection.month == 1):
                    next_collection = next_collection.replace(year=next_year)
                else:
                    next_collection = next_collection.replace(year=current_year)

                dict_data = {
                    "type": bin_type,
                    "collectionDate": next_collection.strftime("%d/%m/%Y"),
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y"))
        return bindata
