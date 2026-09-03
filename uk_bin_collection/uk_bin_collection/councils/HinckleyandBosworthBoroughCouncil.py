import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

BASE_URL = "https://www.hinckley-bosworth.gov.uk"


class CouncilClass(AbstractGetBinDataClass):
    """
    Hinckley and Bosworth Borough Council's old iCal bin-collection feed
    has been retired (it now returns "200 text/calendar" with a
    permanently empty body, regardless of what's passed to it). The
    site now surfaces dates through a session-based postcode/address
    search feeding into a plain HTML "all collection dates" page, with
    each date's bin type given as an <img alt="..."> icon rather than
    text - no Selenium needed, just a real session (cookies) carried
    across the postcode search -> address selection -> dates page.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)
        check_paon(user_paon)
        data = {"bins": []}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        s = requests.Session()
        s.headers.update(headers)

        r = s.get(
            f"{BASE_URL}/address-search",
            params={"redirect": "refuse", "fpcode": user_postcode},
            timeout=15,
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        address_links = [
            a for a in soup.find_all("a") if "set-location" in (a.get("href") or "")
        ]
        if not address_links:
            raise ValueError(f"No addresses found for postcode {user_postcode}")

        paon_upper = user_paon.strip().upper()
        match = next(
            (
                a
                for a in address_links
                if a.get_text(strip=True).upper().startswith(paon_upper + " ")
            ),
            None,
        )
        if not match:
            raise ValueError(
                f"Could not match house number '{user_paon}' in address results"
            )

        set_location_url = match["href"]
        if set_location_url.startswith("/"):
            set_location_url = BASE_URL + set_location_url
        r2 = s.get(set_location_url, timeout=15)
        r2.raise_for_status()
        soup2 = BeautifulSoup(r2.text, "html.parser")

        # Selecting an address sets session state remembering it, and the
        # resulting page links to the full year of dates for the round
        # that address is on.
        round_link = soup2.find("a", href=lambda h: h and "round=" in h)
        if not round_link:
            raise ValueError("Could not determine collection round for this address")

        r3 = s.get(f"{BASE_URL}{round_link['href']}", timeout=15)
        r3.raise_for_status()
        soup3 = BeautifulSoup(r3.text, "html.parser")

        # Dates are listed in strict chronological order starting from
        # today with no year in the text - track year rollovers by month
        # decreasing rather than assuming everything is this calendar year.
        current_year = datetime.now().year
        last_month = None

        for row in soup3.select('div[class*="date_bins"]'):
            heading = row.find("h3")
            if not heading:
                continue
            try:
                parsed = datetime.strptime(
                    heading.get_text(strip=True).rstrip(":"), "%A %d %B"
                )
            except ValueError:
                continue

            if last_month is not None and parsed.month < last_month:
                current_year += 1
            last_month = parsed.month
            collection_date = parsed.replace(year=current_year)

            for img in row.find_all("img"):
                bin_type = (img.get("alt") or "").strip()
                if not bin_type:
                    continue
                data["bins"].append(
                    {
                        "type": bin_type.capitalize(),
                        "collectionDate": collection_date.strftime(date_format),
                    }
                )

        data["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], date_format)
        )
        return data
