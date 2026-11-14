import re
import time
from datetime import datetime, timedelta

import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

BASE_URL = "https://eastcambs-self.achieveservice.com"
SERVICE_URL = f"{BASE_URL}/service/Check_your_waste_collection_day"

# AchieveForms lookup IDs from the "Waste collections calendar" form
# (new service from 1 June 2026, replacing the old custompage).
LOOKUP_AUTH = "64f7354c7f8a9"
LOOKUP_ADDRESSES = "54915cbced788"
LOOKUP_COMMUNAL = "69e0b75da3d0b"
LOOKUP_COLLECTIONS = "6784e74793b68"

# The collections lookup returns only the *last* date per bin type inside
# [MinimumDateForNextDates, MaximumDateFormattedNext) (max is exclusive).
# Querying consecutive 7-day windows gives exactly one occurrence per bin
# type per window, so every collection in the period is captured.
WINDOW_DAYS = 7
WINDOW_COUNT = 4


class CouncilClass(AbstractGetBinDataClass):
    """
    East Cambridgeshire moved to a new AchieveForms (Firmstep) form on
    1 June 2026. Collections come from the form's apibroker lookups.
    """

    def _run_lookup(self, session, sid, lookup_id, values):
        form_values = {"Section 1": {k: {"value": v} for k, v in values.items()}}
        response = session.post(
            f"{BASE_URL}/apibroker/runLookup",
            params={
                "id": lookup_id,
                "repeat_against": "",
                "noRetry": "true",
                "getOnlyTokens": "undefined",
                "log_id": "",
                "app_name": "AF-Renderer::Self",
                "_": str(int(time.time() * 1000)),
                "sid": sid,
            },
            json={"formValues": form_values},
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        transformed = result.get("integration", {}).get("transformed")
        if result.get("status") != "done" or transformed is None:
            raise ValueError(
                f"East Cambridgeshire lookup {lookup_id} failed: "
                f"{result.get('error')}"
            )
        rows = transformed.get("rows_data") or {}
        # rows_data is a dict keyed by row id, or an empty list when no rows.
        return list(rows.values()) if isinstance(rows, dict) else []

    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        postcode = kwargs.get("postcode")
        paon = kwargs.get("paon") or kwargs.get("house_number")

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
                )
            }
        )

        # Load the service (redirects to the AchieveForms page) and get a sid.
        form_page = session.get(SERVICE_URL, timeout=30)
        form_page.raise_for_status()
        auth = session.get(
            f"{BASE_URL}/authapi/isauthenticated",
            params={
                "uri": form_page.url,
                "hostname": "eastcambs-self.achieveservice.com",
                "withCredentials": "true",
            },
            timeout=30,
        )
        auth.raise_for_status()
        sid = auth.json().get("auth-session")
        if not sid:
            raise ValueError("Could not obtain East Cambridgeshire form session")

        auth_rows = self._run_lookup(session, sid, LOOKUP_AUTH, {})
        if not auth_rows or not auth_rows[0].get("AuthenticateResponse"):
            raise ValueError("Could not obtain East Cambridgeshire auth token")
        token = auth_rows[0]["AuthenticateResponse"]

        if not uprn:
            if not postcode:
                raise ValueError("Provide a UPRN, or a postcode and house number")
            addresses = self._run_lookup(
                session,
                sid,
                LOOKUP_ADDRESSES,
                {"AuthenticateResponse": token, "PostcodeSearch": postcode},
            )
            if not addresses:
                raise ValueError(f"No addresses found for postcode {postcode}")
            if paon:
                paon_pattern = re.compile(
                    rf"(?<!\w){re.escape(str(paon).strip())}(?!\w)", re.IGNORECASE
                )
                match = next(
                    (a for a in addresses if paon_pattern.match(a.get("display", ""))),
                    None,
                ) or next(
                    (a for a in addresses if paon_pattern.search(a.get("display", ""))),
                    None,
                )
                if not match:
                    raise ValueError(
                        f"Could not match house number/name '{paon}' among "
                        f"{len(addresses)} addresses for postcode {postcode}"
                    )
            else:
                match = addresses[0]
            uprn = match["uprn"]

        check_uprn(uprn)
        uprn = str(uprn)

        # Flats on a communal collection use the parent property's UPRN.
        selected_uprn = uprn
        communal = self._run_lookup(
            session,
            sid,
            LOOKUP_COMMUNAL,
            {"AuthenticateResponse": token, "selected_uprn": uprn},
        )
        if (
            communal
            and str(communal[0].get("HasCommunal", "")).lower() == "true"
            and communal[0].get("CommunalUPRN")
        ):
            selected_uprn = communal[0]["CommunalUPRN"]

        collections = set()
        start = datetime.now().date()
        for i in range(WINDOW_COUNT):
            window_start = start + timedelta(days=i * WINDOW_DAYS)
            window_end = window_start + timedelta(days=WINDOW_DAYS)
            rows = self._run_lookup(
                session,
                sid,
                LOOKUP_COLLECTIONS,
                {
                    "AuthenticateResponse": token,
                    "selected_uprn": selected_uprn,
                    "MinimumDateForNextDates": window_start.strftime("%Y-%m-%d"),
                    "MaximumDateFormattedNext": window_end.strftime("%Y-%m-%d"),
                },
            )
            for row in rows:
                bin_type = (row.get("name") or "").strip()
                date_text = (row.get("ScheduledStart") or "").strip()
                if not bin_type or not date_text:
                    continue
                try:
                    collection_date = datetime.strptime(date_text, "%d/%m/%Y")
                except ValueError:
                    continue
                collections.add((bin_type.title(), collection_date))

        if not collections:
            raise ValueError(f"No collection dates found for UPRN {uprn}")

        data = {"bins": []}
        for bin_type, collection_date in sorted(collections, key=lambda x: (x[1], x[0])):
            data["bins"].append(
                {
                    "type": bin_type,
                    "collectionDate": collection_date.strftime(date_format),
                }
            )
        return data
