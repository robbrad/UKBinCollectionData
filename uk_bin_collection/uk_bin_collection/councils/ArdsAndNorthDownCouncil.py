from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

ADDRESS_API_URL = "https://ardsandnorthdownbincalendar.azurewebsites.net/api/addresses/{}"


def match_address(options, paon):
    """Pick the option whose label starts with (or contains) the house number/name.

    options: list of (value, label). Prefers "<paon> <street>" over "<paon> <flat>",
    then any whole-word occurrence. Raises ValueError if nothing matches.
    """
    paon = str(paon).strip()
    p = re.escape(paon)
    for pattern in (rf"^{p}[\s,]+[A-Za-z]", rf"^{p}[\s,]", rf"(^|[\s,]){p}([\s,]|$)"):
        for value, label in options:
            if re.search(pattern, label.strip(), re.I):
                return value
    raise ValueError(f"No address matching '{paon}' found for this postcode")


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def find_uprn(self, postcode, paon):
        """Resolve a UPRN from postcode + house number via the council's address API."""
        response = requests.get(
            ADDRESS_API_URL.format(postcode.replace(" ", "").upper()), timeout=30
        )
        response.raise_for_status()
        addresses = response.json().get("addresses") or []
        if not addresses:
            raise ValueError(f"No addresses found for postcode {postcode}")
        options = [(a["uprn"], a.get("addressText", "")) for a in addresses]
        return match_address(options, paon)

    def parse_data(self, page: str, **kwargs) -> dict:
        # UPRN if given, otherwise resolve it from postcode + house number
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon") or kwargs.get("house_number")
        if not user_uprn and user_postcode and user_paon:
            user_uprn = self.find_uprn(user_postcode, user_paon)
        check_uprn(user_uprn)
        bindata = {"bins": []}

        API_URL = (
            "https://collections-ardsandnorthdown.azurewebsites.net/WSCollExternal.asmx"
        )

        # council seems to always be ARD no matter what the old council was
        PAYLOAD = f"""<?xml version="1.0" encoding="utf-8" ?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
                <getRoundCalendarForUPRN  xmlns="http://webaspx-collections.azurewebsites.net/">
                    <council>ARD</council>
                    <UPRN>{user_uprn}</UPRN>
                    <from>Chtml</from>
                </getRoundCalendarForUPRN >
            </soap:Body>
        </soap:Envelope>
        """

        r = requests.post(
            API_URL,
            data=PAYLOAD,
            headers={"Content-Type": "text/xml; charset=utf-8"},
            timeout=30,
        )
        r.raise_for_status()

        # html unescape text
        text = (
            (r.text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&"))
            .split("<getRoundCalendarForUPRNResult>")[-1]
            .split("</getRoundCalendarForUPRNResult>")[0]
        )

        soup = BeautifulSoup(text, "html.parser")

        # Initialize dictionary to store bin dates
        bin_schedule = {}

        # Define regex pattern to capture day and date (e.g., Tue 5 Nov)
        date_pattern = re.compile(r"\b\w{3} \d{1,2} \w{3}\b")

        current_year = datetime.now().year

        # Find each bin collection line, parse date, and add to dictionary
        for bin_info in soup.find_all("b"):
            bin_type = bin_info.text.strip()
            bin_details = bin_info.next_sibling.strip() if bin_info.next_sibling else ""
            # Check for "Today" or "Tomorrow"
            if "Today" in bin_details:
                collection_date = datetime.now().strftime("%a %d %b")
                bin_schedule[bin_type] = collection_date
            elif "Tomorrow" in bin_details:
                collection_date = (datetime.now() + timedelta(days=1)).strftime(
                    "%a %d %b"
                )
                bin_schedule[bin_type] = collection_date
            else:
                # Extract date if it's a full date format
                date_match = date_pattern.search(bin_details)
                if date_match:
                    bin_schedule[bin_type] = date_match.group()

        # Display the parsed schedule with dates only
        for bin_type, collection_date in bin_schedule.items():
            date = datetime.strptime(collection_date, "%a %d %b")

            if date.month == 1 and datetime.now().month > 1:
                date = date.replace(year=current_year + 1)
            else:
                date = date.replace(year=current_year)

            dict_data = {
                "type": bin_type,
                "collectionDate": date.strftime("%d/%m/%Y"),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )
        return bindata
