from datetime import datetime, timedelta
from typing import Any
import requests
from icalevents.icalevents import events

from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
from uk_bin_collection.uk_bin_collection.common import date_format


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs: Any) -> dict:
        ics_url: str = kwargs.get("url")

        if not ics_url:
            raise ValueError("Missing required argument: url")

        # Get events within the next 90 days
        now = datetime.now()
        future = now + timedelta(days=60)

        try:
            upcoming_events = events(ics_url, start=now, end=future)
        except Exception as e:
            raise ValueError(f"Error parsing ICS feed: {e}")

        bindata = {"bins": []}

        for event in sorted(upcoming_events, key=lambda e: e.start):
            if not event.summary or not event.start:
                continue

            bindata["bins"].append(
                {
                    "type": event.summary,
                    "collectionDate": event.start.date().strftime(date_format),
                }
            )

        return bindata
