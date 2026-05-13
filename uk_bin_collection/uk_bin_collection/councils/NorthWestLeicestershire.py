import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    AUTOCOMPLETE_URL = (
        "https://my.nwleics.gov.uk/data/ac/addresses.json"
    )
    LOCATION_URL = "https://my.nwleics.gov.uk/location"
    HOME_URL = "https://my.nwleics.gov.uk/"

    def parse_data(self, page: str, **kwargs) -> dict:
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)

        nwl_id = self._resolve_address(user_postcode, user_paon)

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            }
        )

        session.get(
            self.LOCATION_URL,
            params={"put": nwl_id, "rememberme": "0", "redirect": "/"},
            allow_redirects=True,
        )

        response = session.get(self.HOME_URL)
        soup = BeautifulSoup(response.text, features="html.parser")

        refuse_list = soup.find("ul", class_="refuse")
        if not refuse_list:
            raise ValueError(
                "No refuse collection data found for this address"
            )

        data = {"bins": []}
        current_year = datetime.now().year
        current_date = datetime.now().date()

        for li in refuse_list.find_all("li"):
            date_tag = li.find("strong", class_="date")
            link_tag = li.find("a")
            if not date_tag or not link_tag:
                continue

            date_str = date_tag.text.strip()
            waste_type = link_tag.text.strip()

            if date_str.lower() == "today":
                parsed_date = current_date
            elif date_str.lower() == "tomorrow":
                parsed_date = current_date + timedelta(days=1)
            else:
                date_str = re.sub(r"(st|nd|rd|th)", "", date_str)
                parsed_date = datetime.strptime(date_str, "%a %d %b").date()

            if parsed_date.year < current_date.year:
                parsed_date = parsed_date.replace(year=current_year)

            if parsed_date < current_date:
                parsed_date = parsed_date.replace(year=current_year + 1)

            data["bins"].append(
                {
                    "type": waste_type,
                    "collectionDate": parsed_date.strftime(date_format),
                }
            )

        return data

    def _resolve_address(self, postcode: str, house_number: str = None) -> str:
        response = requests.get(
            self.AUTOCOMPLETE_URL, params={"term": postcode}
        )
        response.raise_for_status()
        results = response.json()

        if not results:
            raise ValueError(f"No addresses found for postcode {postcode}")

        if house_number:
            house_lower = house_number.lower().strip()
            for entry in results:
                label = entry.get("label", "").lower()
                if label.startswith(house_lower + ",") or label.startswith(
                    house_lower + " "
                ):
                    return entry["value"]

        if len(results) == 1:
            return results[0]["value"]

        raise ValueError(
            f"Multiple addresses found for {postcode} — provide house_number to disambiguate"
        )
