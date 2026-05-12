import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        user_uprn = kwargs.get("uprn")
        check_postcode(user_postcode)

        base = "https://app.newark-sherwooddc.gov.uk/bincollection"

        s = requests.Session()
        s.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            }
        )

        # Step 1: GET form to obtain ASP.NET tokens
        r1 = s.get(f"{base}/", verify=False)
        r1.raise_for_status()
        soup1 = BeautifulSoup(r1.text, "html.parser")

        viewstate = soup1.find("input", id="__VIEWSTATE")["value"]
        viewstate_gen = soup1.find("input", id="__VIEWSTATEGENERATOR")["value"]
        event_val = soup1.find("input", id="__EVENTVALIDATION")["value"]

        # Step 2: POST postcode search via __doPostBack
        search_query = user_postcode
        if user_paon:
            search_query = f"{user_postcode} {user_paon}"

        form_data = {
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstate_gen,
            "__EVENTVALIDATION": event_val,
            "__EVENTTARGET": "ctl00$MainContent$LinkButtonSearch",
            "__EVENTARGUMENT": "",
            "ctl00$MainContent$TextBoxSearch": search_query,
        }

        r2 = s.post(f"{base}/", data=form_data, verify=False)
        r2.raise_for_status()
        soup2 = BeautifulSoup(r2.text, "html.parser")

        # Step 3: Find address links (collection.aspx?pid=UPRN)
        address_links = []
        for a in soup2.find_all("a"):
            href = a.get("href", "")
            if "collection.aspx" in href and "pid=" in href:
                pid = re.search(r"pid=(\d+)", href)
                if pid:
                    address_links.append(
                        {
                            "text": a.text.strip(),
                            "pid": pid.group(1),
                            "href": href,
                        }
                    )

        if not address_links:
            raise ValueError(
                f"No addresses found for postcode {user_postcode}"
            )

        # Step 4: Select address by UPRN, house number, or first match
        selected = None
        if user_uprn:
            for addr in address_links:
                if addr["pid"] == str(user_uprn):
                    selected = addr
                    break

        if not selected and user_paon:
            paon_lower = user_paon.lower()
            for addr in address_links:
                if addr["text"].lower().startswith(paon_lower):
                    selected = addr
                    break
            if not selected:
                for addr in address_links:
                    if paon_lower in addr["text"].lower():
                        selected = addr
                        break

        if not selected:
            selected = address_links[0]

        # Step 5: GET calendar page (uses same pid as collection.aspx)
        collection_url = f"{base}/calendar?pid={selected['pid']}"
        r3 = s.get(collection_url, verify=False)
        r3.raise_for_status()
        soup3 = BeautifulSoup(r3.text, "html.parser")

        # Step 6: Parse collection dates
        today = datetime.today()
        eight_weeks = today + timedelta(days=8 * 7)
        data = {"bins": []}

        for month in soup3.select('table[class*="table table-condensed"]'):
            info = month.find_all("tr")
            if not info:
                continue
            month_year = info[0].text.strip()
            info.pop(0)

            for item in info:
                text = item.text.strip()
                if "," not in text:
                    continue
                bin_type = text.split(",")[0].strip()
                date_str = text.split(",")[1].strip() + " " + month_year
                try:
                    bin_date = datetime.strptime(
                        remove_ordinal_indicator_from_date_string(date_str),
                        "%A %d %B %Y",
                    )
                except ValueError:
                    continue

                if (
                    today.date() <= bin_date.date() <= eight_weeks.date()
                    and "cancelled" not in bin_type.lower()
                ):
                    data["bins"].append(
                        {
                            "type": bin_type,
                            "collectionDate": bin_date.strftime(date_format),
                        }
                    )

        if not data["bins"]:
            raise ValueError("No collection data found")

        return data
