from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
import requests
from datetime import datetime
from dateutil.parser import parse as dateutil_parse
from dateutil.parser import ParserError
from yarl import URL

from uk_bin_collection.uk_bin_collection.common import check_uprn, check_postcode
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
}


def _parse_collection_date(raw_date: str, today: datetime) -> datetime:
    """
    Parse a 'Weekday DD Month' string (year omitted). Schedules only ever
    contain current/future dates plus a just-completed entry from the past
    week, so year rollover only ever happens at the Dec->Jan boundary -
    never mid-year.
    """
    try:
        parsed = dateutil_parse(raw_date, default=today, fuzzy=True)
    except (ParserError, ValueError, OverflowError) as exc:
        raise ValueError(
            f"Could not parse Birmingham collection date: {raw_date!r}"
        ) from exc        


    # We only have day and month so handle year crossover boundaries
    # If we are in Jan/Feb/Mar and the parsed date is in Oct/Nov/Dec assume date is last year
    # If we are in Oct/Nov/Dec and the parsed date is in Jan/Feb/Mar assume date is next year
    if parsed.month <= 3 and today.month >= 10:
        parsed = parsed.replace(year=parsed.year + 1)
    elif parsed.month >= 10 and today.month <= 3:
        parsed = parsed.replace(year=parsed.year - 1)

    return parsed

class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs: Any) -> Dict[str, List[Dict[str, str]]]:
        """
        Parse the council HTML page and return upcoming bin collection dates for the given address.
        
        Parameters:
            page (str): HTML content of the initial council page used to extract the form token.
            uprn (str): Unique Property Reference Number for the address; required.
            postcode (str): Postal code for the address; required.
        
        Returns:
            Dict[str, List[Dict[str, str]]]: A dictionary with a single key "bins" mapping to a list of bin objects.
                Each bin object contains:
                    - "type": the bin type as displayed on the site (e.g., "General waste").
                    - "collectionDate": the next collection date formatted according to the module's `date_format`.
        
        Raises:
            ValueError: If `uprn` or `postcode` is not provided.
        """
        uprn: Optional[str] = kwargs.get("uprn")
        postcode: Optional[str] = kwargs.get("postcode")

        if uprn is None:
            raise ValueError("UPRN is required and must be a non-empty string.")
        if postcode is None:
            raise ValueError("Postcode is required and must be a non-empty string.")

        check_uprn(uprn)
        check_postcode(postcode)

        requests.packages.urllib3.disable_warnings()

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        }


        query_string = {
            "postcode": postcode,
            "uprn": uprn,
        }
        url = URL("https://www.birmingham.gov.uk/info/50388/check_your_collection_day").with_query(query_string)
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        bins_data = {"bins": []}
        if not (table := soup.find("table", class_="data-table")):
            raise ValueError("Could not find the collection dates table in the council page.")
        if not (body := table.find("tbody")):
            raise ValueError("Could not find the table body in the collection dates table.")
        rows = body.find_all("tr")

        today = datetime.now()
        for row in rows:
            cells = row.find_all(["th", "td"])
            if cells is None or len(cells) < 2:
                raise ValueError("Unexpected table row structure; expected at least two cells.")
            date_str = cells[0].get_text(strip=True)
            bin_type = cells[1].get_text(strip=True)

            parsed_date = _parse_collection_date(date_str, today)
            if parsed_date.date() < today.date():
                continue

            bins_data["bins"].append(
                {"type": bin_type, "collectionDate": parsed_date.strftime(date_format)}
            )

        bins_data["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], date_format)
        )
        return bins_data
    