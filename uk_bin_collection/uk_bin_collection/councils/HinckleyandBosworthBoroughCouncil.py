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
        user_uprn = str(user_uprn).zfill(12)
        check_uprn(user_uprn)
        bindata = {"bins": []}

        ics_url = f"https://www.hinckley-bosworth.gov.uk/bin-collection-feed?round={user_uprn}"

        # Get events from ICS file within the next 365 days
        now = datetime.now()
        future = now + timedelta(days=365)

        # Parse ICS calendar
        upcoming_events = events(ics_url, start=now, end=future)

        for event in sorted(upcoming_events, key=lambda e: e.start):
            if event.summary and event.start:
                collections = event.summary.split(",")
                for collection in collections:
                    if collection.strip() == "bin collection":
                        collection = "food waste caddy"
                    collection = collection.strip().replace(" collection", "")
                    bindata["bins"].append(
                        {
                            "type": collection,
                            "collectionDate": event.start.date().strftime(date_format),
                        }
                    )

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata
