import re
import time
from datetime import datetime, timedelta

import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

HOST = "forms.towerhamlets.gov.uk"
PROCESS_ID = "AF-Process-7693495e-0aa2-4438-872c-2a6e5f3da446"
STAGE_ID = "AF-Stage-4c6e80ac-7dc2-46e4-afa6-fd46d11565ec"

# Lookups run by the council's AchieveForms "check your collection days" form
ADDRESS_LOOKUP = "679a078a246c0"  # postcodeCustomerEntry -> display, name (UPRN)
DATES_LOOKUP = "654ba9e6a9886"  # TH_uprn, NextCollectionFromDate -> CollectionService, CollectionDate
TIMEBAND_LOOKUP = "69370cda669e0"  # TH_uprn -> single_AM_Timeband, single_PM_Timeband

DAILY_DAYS = 7
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
)


class AchieveFormsSession:
    """Calls the form's server-side lookups directly, without a browser."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        form_uri = (
            f"https://{HOST}/AchieveForms/?mode=fill&consentMessage=yes"
            f"&form_uri=sandbox-publish://{PROCESS_ID}/{STAGE_ID}/definition.json"
            f"&process=1&process_uri=sandbox-processes://{PROCESS_ID}&process_id={PROCESS_ID}"
        )
        response = self.session.get(
            f"https://{HOST}/authapi/isauthenticated",
            params={"uri": form_uri, "hostname": HOST, "withCredentials": "true"},
            timeout=30,
        )
        response.raise_for_status()
        self.sid = response.json()["auth-session"]

    def lookup(self, lookup_id, fields):
        """Run a lookup with {field: value}; returns its rows as [{column: value}]."""
        response = self.session.post(
            f"https://{HOST}/apibroker/runLookup",
            params={
                "id": lookup_id,
                "repeat_against": "",
                "noRetry": "true",
                "getOnlyTokens": "undefined",
                "log_id": "",
                "app_name": "AF-Renderer::Self",
                "_": str(int(time.time() * 1000)),
                "sid": self.sid,
            },
            json={
                "formValues": {
                    "Section 1": {
                        name: {"value": value} for name, value in fields.items()
                    }
                }
            },
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"https://{HOST}/fillform/?iframe_id=fillform-frame-1&db_id=",
            },
            timeout=30,
        )
        response.raise_for_status()
        xml = response.json().get("data", "")
        return [
            dict(re.findall(r'column="([^"]+)" [Ii]s[Nn]ull="[^"]*">([^<]*)<', row))
            for row in re.findall(r"<Row [^>]*>(.*?)</Row>", xml, re.DOTALL)
        ]


def with_year(day_month, today):
    """'05 October' -> the next such date (dates are listed without a year)."""
    for year in (today.year, today.year + 1):
        try:
            parsed = datetime.strptime(f"{day_month} {year}", "%d %B %Y").date()
        except ValueError:  # 29 February outside a leap year
            continue
        if parsed >= today - timedelta(days=31):
            return parsed
    raise ValueError(f"Unparseable collection date {day_month!r}")


class CouncilClass(AbstractGetBinDataClass):
    """
    Tower Hamlets' collection days come from an AchieveForms form. The form
    now lists upcoming dates in a table (the single-value fields it used to
    fill are empty for most addresses), so call its lookups directly.

    Streets with time-banded collections (bags out at set times, collected
    daily) have no dates; their time bands come from a separate lookup.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        form = AchieveFormsSession()

        if not user_uprn:
            check_postcode(user_postcode)
            user_uprn = self.find_uprn(form, user_postcode, user_paon)
        check_uprn(user_uprn)

        today = datetime.now().date()
        data = {"bins": []}
        for row in form.lookup(
            DATES_LOOKUP,
            {
                "TH_uprn": user_uprn,
                "NextCollectionFromDate": today.strftime("%d/%m/%Y"),
            },
        ):
            if row.get("CollectionService") and row.get("CollectionDate"):
                data["bins"].append(
                    {
                        "type": row["CollectionService"],
                        "collectionDate": with_year(
                            row["CollectionDate"], today
                        ).strftime(date_format),
                    }
                )

        if not data["bins"]:
            bands = next(iter(form.lookup(TIMEBAND_LOOKUP, {"TH_uprn": user_uprn})), {})
            parts = [
                f"{half}: {bands[f'single_{half}_Timeband']}"
                for half in ("AM", "PM")
                if bands.get(f"single_{half}_Timeband")
            ]
            if parts:
                bin_type = f"Daily Collection ({' / '.join(parts)})"
                for i in range(DAILY_DAYS):
                    data["bins"].append(
                        {
                            "type": bin_type,
                            "collectionDate": (today + timedelta(days=i)).strftime(
                                date_format
                            ),
                        }
                    )

        if not data["bins"]:
            raise ValueError(f"No collection data found for UPRN {user_uprn}")
        return data

    @staticmethod
    def find_uprn(form, postcode, paon):
        """The UPRN of the address at postcode starting with paon (or the first)."""
        addresses = form.lookup(
            ADDRESS_LOOKUP,
            {
                "postcodeCustomerEntry": postcode,
                "postcodeToUse": postcode.replace(" ", ""),
                "Version": "1.1",
            },
        )
        addresses = [a for a in addresses if a.get("name")]
        if not addresses:
            raise ValueError(f"No addresses found for postcode {postcode}")
        paon = (paon or "").strip().lower()
        for address in addresses:
            label = address.get("display", "").lower()
            if paon and (label.startswith(paon + ",") or label.startswith(paon + " ")):
                return address["name"]
        if paon:
            raise ValueError(
                f"No address matching {paon!r} found for postcode {postcode}"
            )
        return addresses[0]["name"]
