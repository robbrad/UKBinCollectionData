from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # Get and check UPRN
        user_uprn = kwargs.get("uprn")
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
