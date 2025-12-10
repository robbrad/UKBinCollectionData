from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from icalevents.icalevents import events

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:

        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        URI = f"https://www.renfrewshire.gov.uk/bins-and-recycling/bin-collection/bin-collection-calendar/check-your-bin-collection-day/view/{user_uprn}"

        # Make the GET request
        response = requests.get(URI)

        soup = BeautifulSoup(response.text, features="html.parser")
        a = soup.find("a", href=lambda h: h and h.lower().endswith(".ics"))
        if a:
            ics_url = "https://www.renfrewshire.gov.uk" + a["href"]
        else:
            raise ValueError(
                f"Could not find collection ICS file for UPRN: {user_uprn}"
            )

        # Get events from ICS file within the next 365 days
        now = datetime.now()
        future = now + timedelta(days=365)

        # Parse ICS calendar
        upcoming_events = events(ics_url, start=now, end=future)

        for event in sorted(upcoming_events, key=lambda e: e.start):
            if event.summary and event.start:
                collections = event.summary.split(",")
                for collection in collections:
                    bindata["bins"].append(
                        {
                            "type": collection.strip(),
                            "collectionDate": event.start.date().strftime(date_format),
                        }
                    )

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
