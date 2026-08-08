from datetime import timedelta
import re
from abc import abstractmethod
import requests
from bs4 import BeautifulSoup
from icalevents.icalparser import parse_events

from uk_bin_collection.uk_bin_collection.common import date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class SocietyWorksClass(AbstractGetBinDataClass):
    """
    Shared implementation for services using the same backend software by SocietyWorks
    """

    @property
    @abstractmethod
    def BASE_URL(self):
        pass

    def __init__(self, *args, **kwargs):
        """Set up a shared requests session"""
        super().__init__(*args, **kwargs)
        self.session = requests.Session()
        headers = {
            "User-Agent": "uk-bin-collection/1.0 (+https://github.com/robbrad/UKBinCollectionData)",
        }
        self.session.headers.update(headers)

    def _get(self, url):
        resp = self.session.get(
            f"{self.BASE_URL}{url}", allow_redirects=False, timeout=30
        )
        return resp

    def _uprn_to_property_id(self, uprn):
        """Takes a UPRN (might be a property ID) and tries to look up a property ID"""
        resp = self._get(f"property/{uprn}")
        if resp.status_code == 404:
            # If no lookup, assume we might have been given a property ID directly
            return uprn
        resp.raise_for_status()
        location = resp.headers["Location"]
        property_id = location.split("/")[-1]
        return property_id

    def _address_to_property_id(self, postcode, addr):
        """Takes a postcode and address line and looks up its property ID"""
        resp = self.session.post(
            f"{self.BASE_URL}waste", data={"postcode": postcode}, timeout=30
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        select = soup.find("select", {"id": "address"})
        if not select:
            return None
        addr_lower = (addr or "").strip().lower()
        address_list = select.find_all("option")
        for address in address_list:
            text = address.get_text(strip=True).lower()
            if addr_lower in text:
                return address.get("value")
        return None

    def parse_data(self, page: str, **kwargs) -> dict:
        """Takes provided user data and fetches bin day iCal information"""
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        user_url = kwargs.get("url")

        property_id = None
        # Keep handling Bromley/Kingston old way, with ID in passed URL
        if m := re.search("waste/([0-9]+)", user_url):
            property_id = m.group(1)
        elif user_uprn:
            if not user_uprn.isdigit():
                raise ValueError("Invalid UPRN/ID")
            property_id = self._uprn_to_property_id(user_uprn)
        elif user_postcode and user_paon:
            property_id = self._address_to_property_id(user_postcode, user_paon)

        if not property_id:
            raise ValueError(
                "Could not resolve property. Provide postcode+address or valid UPRN."
            )

        resp = self._get(f"waste/{property_id}/calendar.ics")
        resp.raise_for_status()
        text = resp.text
        if "VCALENDAR" not in text:
            raise ValueError(
                f"ICS feed returned invalid data for ID {property_id} (status {resp.status_code})"
            )

        data = {"bins": []}
        collections = parse_events(text, default_span=timedelta(days=60), sort=True)
        for event in collections:
            if event.summary and event.start:
                data["bins"].append(
                    {
                        "type": event.summary,
                        "collectionDate": event.start.date().strftime(date_format),
                    }
                )

        return data
