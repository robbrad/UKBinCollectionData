from datetime import datetime
from typing import Any
import requests
from ics import Calendar

from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
from uk_bin_collection.uk_bin_collection.common import date_format


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs: Any) -> dict:
        ics_url: str = kwargs.get("url")

        if not ics_url:
            raise ValueError("Missing required argument: google_calendar_ics_url")

        response = requests.get(ics_url)
        response.raise_for_status()

        calendar = Calendar(response.text)
        bindata = {"bins": []}

        for event in calendar.events:
            if not event.name or not event.begin:
                continue

            try:
                # .begin is a datetime-like object (Arrow)
                collection_date = event.begin.date().strftime(date_format)
            except Exception:
                continue

            bindata["bins"].append({
                "type": event.name,
                "collectionDate": collection_date
            })

        return bindata
