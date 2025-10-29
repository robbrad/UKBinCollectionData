import re
import time
from datetime import date, datetime

import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        try:
            data = {"bins": []}

            user_paon = kwargs.get("paon")

            check_paon(user_paon)

            url = "https://api.eu.recollect.net/api/areas/MiddlesbroughUK/services/50005/address-suggest"
            params = {
                "q": user_paon,
                "locale": "en-GB",
                "_": str(int(time.time() * 1000)),
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            }

            response = requests.get(url, headers=headers, params=params)

            addresses = response.json()
            for address in addresses:
                if "place_id" in address:
                    place_id = address["place_id"]
                    break

            if not place_id:
                print(f"An error occurred: retrieving the address")
                return

            url = "https://api.eu.recollect.net/api/areas/MiddlesbroughUK/services/50005/pages/en-GB/place_calendar.json?widget_config=%7B%22area%22%3A%22MiddlesbroughUK%22%2C%22name%22%3A%22calendar%22%2C%22base%22%3A%22https%3A%2F%2Frecollect.net%22%2C%22third_party_cookie_enabled%22%3A1%2C%22place_not_found_in_guest%22%3A0%2C%22is_guest_service%22%3A0%7D"
            params = {
                "q": user_paon,
                "locale": "en-GB",
                "_": str(int(time.time() * 1000)),
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "x-recollect-place": place_id + ":50005",
            }
            response = requests.get(url, headers=headers, params=params)
            # response = response.json()

            def extract_next_collection(payload: dict):
                # 1) Find the "Next Collection" section
                sections = payload.get("sections", [])
                next_col_section = next(
                    (s for s in sections if s.get("title") == "Next Collection"), None
                )
                if not next_col_section:
                    return None

                rows = next_col_section.get("rows", [])

                # 2) First row is the date inside <strong>…</strong>
                next_date = None
                if rows and rows[0].get("type") == "html":
                    html = rows[0].get("html", "")
                    # grab text inside <strong>…</strong>
                    m = re.search(r"<strong>(.*?)</strong>", html, flags=re.I | re.S)
                    if m:
                        date_text = m.group(1).strip()
                        # e.g. "Wednesday, October 29, 2025"
                        try:
                            next_date = datetime.strptime(
                                date_text, "%A, %B %d, %Y"
                            ).date()
                        except ValueError:
                            # Fallback: strip tags and leave raw text if format changes
                            next_date = date_text

                # 3) Remaining rows of type "rich-content" hold the bin types
                bins = []
                for r in rows[1:]:
                    if r.get("type") == "rich-content":
                        label = r.get("label") or r.get(
                            "html"
                        )  # "Refuse", "Recycling", etc.
                        flag = (r.get("data") or {}).get(
                            "flag"
                        )  # "REFUSE", "RECYCLING", etc.
                        if label or flag:
                            bins.append({"label": label, "flag": flag})

                return {"date": next_date, "bins": bins}

            # Example:
            result = extract_next_collection(response.json())

            if result and result.get("date") and result.get("bins"):
                d = result["date"]
                formatted_date = (
                    d.strftime(date_format) if isinstance(d, date) else str(d)
                )

                for b in result["bins"]:
                    bin_type = b.get("label") or b.get(
                        "flag"
                    )  # e.g., "Refuse" or "RECYCLING"
                    if not bin_type:
                        continue
                    data["bins"].append(
                        {"type": bin_type, "collectionDate": formatted_date}
                    )
            return data

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
