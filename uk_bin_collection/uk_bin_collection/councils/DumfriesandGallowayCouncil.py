import re
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from icalevents.icalevents import events

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

SEARCH_URL = "https://www.dumfriesandgalloway.gov.uk/bins-recycling/waste-collection-schedule/find"
ICS_BASE = "https://www.dumfriesandgalloway.gov.uk/bins-recycling/waste-collection-schedule/download"


def _resolve_uprn(postcode, uprn=None, paon=None):
    """Resolve UPRN via postcode address search if not provided."""
    if uprn:
        return str(uprn)

    if not postcode:
        raise ValueError("Provide a postcode or UPRN.")

    resp = requests.get(SEARCH_URL, params={"postcode": postcode}, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    select_el = soup.find("select", {"name": "uprn"})
    if not select_el:
        raise ValueError(f"No addresses found for postcode: {postcode}")

    options = [(opt["value"], opt.text.strip()) for opt in select_el.find_all("option") if opt.get("value")]
    if not options:
        raise ValueError(f"No addresses found for postcode: {postcode}")

    if paon:
        paon_norm = str(paon).strip().upper()
        for val, text in options:
            text_upper = text.upper()
            if text_upper.startswith(paon_norm + " ") or text_upper.startswith(paon_norm + ","):
                return val
        for val, text in options:
            if paon_norm in text.upper():
                return val

    return options[0][0]


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        driver = None
        try:
            data = {"bins": []}

            user_uprn = kwargs.get("uprn")
            user_postcode = kwargs.get("postcode")
            user_paon = kwargs.get("paon")

            resolved_uprn = _resolve_uprn(user_postcode, uprn=user_uprn, paon=user_paon)

            ics_url = f"{ICS_BASE}/{resolved_uprn}"

            import requests as req
            ics_resp = req.get(ics_url, timeout=30)
            ics_text = ics_resp.text
            if "<br" in ics_text or "<html" in ics_text.lower() or "VCALENDAR" not in ics_text:
                return data

            now = datetime.now()
            future = now + timedelta(days=60)

            upcoming_events = events(ics_url, start=now, end=future)

            for event in sorted(upcoming_events, key=lambda e: e.start):
                if event.summary and event.start:
                    collections = event.summary.split(",")
                    for collection in collections:
                        data["bins"].append(
                            {
                                "type": collection.strip(),
                                "collectionDate": event.start.date().strftime(
                                    date_format
                                ),
                            }
                        )
        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        finally:
            if driver:
                driver.quit()

        return data
