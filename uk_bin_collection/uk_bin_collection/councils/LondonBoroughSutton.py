import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

def remove_ordinal_indicator_from_date_string(date_str):
    return re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)

class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        bindata = {"bins": []}

        URI = f"https://waste-services.sutton.gov.uk/waste/{user_uprn}"

        # --- Session with polite retry policy
        s = requests.Session()
        s.headers.update({
            "User-Agent": "uk-bin-collection/1.0 (+https://github.com/robbrad/UKBinCollectionData)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Connection": "close",
        })
        retry = Retry(
            total=5,
            backoff_factor=1.5,             # 0, 1.5s, 3s, 4.5s, 6s...
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            respect_retry_after_header=True
        )
        s.mount("https://", HTTPAdapter(max_retries=retry))
        s.mount("http://", HTTPAdapter(max_retries=retry))

        # --- Initial fetch with timeout
        r = s.get(URI, timeout=20)
        # If 429 and Retry-After present, requests+urllib3 will already honor it.
        r.raise_for_status()

        # --- Poll only if the page explicitly says it's still loading
        # Use exponential backoff and a hard cap to avoid rate limits
        max_polls = 5           # don't keep hammering
        delay = 2.0
        poll = 0
        while "Loading your bin days..." in r.text and poll < max_polls:
            time.sleep(delay)
            delay = min(delay * 2, 30)  # grow delay but cap it
            r = s.get(URI, timeout=20)
            if r.status_code == 429:
                # manual respect if upstream Retry didn’t catch (e.g., no header)
                retry_after = int(r.headers.get("Retry-After", "10"))
                time.sleep(min(retry_after, 60))
            r.raise_for_status()
            poll += 1

        if "Loading your bin days..." in r.text:
            # fail fast with a clear message so callers can back off scheduling
            raise RuntimeError(
                "Sutton page still loading after polite retries; back off and try later."
            )

        soup = BeautifulSoup(r.content, "html.parser")
        current_year = datetime.now().year
        next_year = current_year + 1

        services = soup.find_all("h3")
        for service in services:
            bin_type = service.get_text(strip=True)
            if "Bulky Waste" in bin_type:
                continue

            # Walk a few siblings to find 'Next collection'
            next_coll = None
            sib = service
            for _ in range(4):
                sib = sib.find_next_sibling() if sib else None
                if not sib:
                    break
                text = sib.get_text(" ", strip=True) if hasattr(sib, "get_text") else str(sib)
                m = re.search(r"Next collection\s*([A-Za-z]+,?\s+\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+)", text)
                if not m:
                    m = re.search(r"Next collection([A-Za-z]+,?\s+\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+)", text)
                if m:
                    next_coll = m.group(1)
                    break

            if not next_coll:
                continue

            next_coll = remove_ordinal_indicator_from_date_string(next_coll)
            try:
                next_dt = datetime.strptime(next_coll, "%A, %d %B")
            except ValueError:
                # Try a looser pattern if the comma is missing
                try:
                    next_dt = datetime.strptime(next_coll, "%A %d %B")
                except ValueError:
                    continue

            # Year roll-over handling
            if datetime.now().month == 12 and next_dt.month == 1:
                next_dt = next_dt.replace(year=next_year)
            else:
                next_dt = next_dt.replace(year=current_year)

            bindata["bins"].append({
                "type": bin_type,
                "collectionDate": next_dt.strftime("%d/%m/%Y"),
            })

        bindata["bins"].sort(key=lambda x: datetime.strptime(x["collectionDate"], "%d/%m/%Y"))
        return bindata
