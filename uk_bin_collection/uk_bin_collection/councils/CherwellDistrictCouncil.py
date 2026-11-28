from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# The search form on www.cherwell.gov.uk now just links out to this "My Account"
# page, which takes the UPRN directly and renders the results.
RESULTS_URL = "https://forms.cherwell.gov.uk/myaccount"
REQUEST_TIMEOUT_SECONDS = 30


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    @staticmethod
    def _full_date(date_str: str, today: date) -> str:
        """Turn e.g. "2nd December" into a dd/mm/YYYY date on or after today."""
        date_str = remove_ordinal_indicator_from_date_string(date_str)
        date_obj = datetime.strptime(f"{date_str} {today.year}", "%d %B %Y")
        if date_obj.date() < today:
            date_obj = datetime.strptime(f"{date_str} {today.year + 1}", "%d %B %Y")
        return date_obj.strftime(date_format)

    @classmethod
    def parse_results(cls, html: str, today: date) -> dict:
        """Parse the results page, raising ValueError if it holds no collections."""
        soup = BeautifulSoup(html, "html.parser")
        tasks_div = soup.select_one(".bin-collection-results__tasks")
        if tasks_div is None:
            raise ValueError(
                "No bin collection results found on the Cherwell page. "
                "Check the UPRN, or the council may have changed its page."
            )

        bins = []
        for item in tasks_div.find_all("li", class_="list__item"):
            heading = item.find("h3", class_="bin-collection-tasks__heading")
            date_tag = item.find("p", class_="bin-collection-tasks__date")
            if not heading or not date_tag:
                continue

            # Skip the visually hidden "Your next ... collection" wording.
            bin_type = "".join(
                text.strip()
                for text in heading.find_all(string=True)
                if "visually-hidden" not in (text.parent.get("class") or [])
            )
            if not bin_type:
                continue

            bins.append(
                {
                    "type": bin_type,
                    "collectionDate": cls._full_date(date_tag.text.strip(), today),
                }
            )

        if not bins:
            raise ValueError("Cherwell results page listed no bin collections.")

        bins.sort(key=lambda x: datetime.strptime(x["collectionDate"], date_format))
        return {"bins": bins}

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        }
        response = requests.get(
            RESULTS_URL,
            params={"uprn": user_uprn},
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        return self.parse_results(response.text, date.today())
