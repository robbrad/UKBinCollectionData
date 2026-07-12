from datetime import timedelta

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Torridge District Council — the old direct SOAP API at
    collections-torridge.azurewebsites.net/WebService2.asmx was retired
    (that host now only serves a staff "Digital Depot" login). The same
    underlying getRoundCalendarForUPRN webservice is now reached through
    the council's Granicus/AchieveForms self-service broker instead.

    Response changed from explicit "Mon 14 Apr" dates to relative phrases
    ("Tomorrow then every Mon", "Today then every Tue", etc.) plus an embedded
    calendar table. This parser handles the relative summary lines and falls
    back to the old explicit date format if it ever reappears.
    """

    WEEKDAYS = {
        "mon": 0,
        "tue": 1,
        "wed": 2,
        "thu": 3,
        "fri": 4,
        "sat": 5,
        "sun": 6,
    }

    HOSTNAME = "torridgedc-self.achieveservice.com"
    PROCESS_ID = "bb925b16-12f7-4233-9b77-c644617535f6"
    STAGE_ID = "a963b8c5-2715-4d5d-805c-18e16c033612"
    CALENDAR_LOOKUP_ID = "65956fdb70ea4"

    def parse_data(self, page, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        if not uprn:
            raise ValueError("UPRN is required")

        api_url = f"https://{self.HOSTNAME}/apibroker/runLookup"
        initial_url = f"https://{self.HOSTNAME}/AchieveForms/"

        s = requests.Session()
        s.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

        # Step 1 - session priming
        r = s.get(
            initial_url,
            params={
                "mode": "fill",
                "consentMessage": "yes",
                "form_uri": f"sandbox-publish://AF-Process-{self.PROCESS_ID}/AF-Stage-{self.STAGE_ID}/definition.json",
                "process": "1",
                "process_uri": f"sandbox-processes://AF-Process-{self.PROCESS_ID}",
                "process_id": f"AF-Process-{self.PROCESS_ID}",
            },
            timeout=30,
        )
        sid_match = re.search(r'"auth-session":"([^"]+)"', r.text)
        if not sid_match:
            raise ValueError("Torridge: could not obtain AchieveForms auth session")
        sid = sid_match.group(1)

        # Step 2 - calendar lookup by UPRN
        r2 = s.post(
            api_url,
            params={
                "id": self.CALENDAR_LOOKUP_ID,
                "repeat_against": "",
                "noRetry": "true",
                "getOnlyTokens": "undefined",
                "log_id": "",
                "app_name": "AF-Renderer::Self",
                "sid": sid,
            },
            json={"formValues": {"Section 1": {"uprn": {"value": str(uprn)}}}},
            timeout=30,
        )
        r2.raise_for_status()
        lookup_data = r2.json()

        rows_data = (
            lookup_data.get("integration", {}).get("transformed", {}).get("rows_data")
            or {}
        )
        inner_html = rows_data.get("0", {}).get("getRoundCalendarForUPRNResponse", "")
        if not inner_html:
            raise ValueError(
                f"Torridge: no calendar data returned for UPRN {uprn}: {lookup_data}"
            )

        soup = BeautifulSoup(inner_html, features="html.parser")
        data = {"bins": []}

        today = datetime.today().date()

        for b in soup.find_all(["b", "B"]):
            bin_type = b.get_text(strip=True)
            if not bin_type:
                continue
            if bin_type.lower().startswith("key"):
                break
            if re.match(r"^[A-Za-z]+\s+\d{4}$", bin_type):
                continue

            nxt = b.next_sibling
            if not isinstance(nxt, str):
                continue
            raw = nxt.strip()
            if not raw.startswith(":"):
                continue
            value = raw.lstrip(":").strip()

            if re.search(r"\bNo\b.*collection", value, re.IGNORECASE):
                continue

            base_date = self._extract_base_date(value, today)
            if base_date is None:
                continue

            data["bins"].append(
                {
                    "type": bin_type,
                    "collectionDate": base_date.strftime(date_format),
                }
            )

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data

    def _extract_base_date(self, value, today):
        vl = value.lower()

        if vl.startswith("today"):
            return today
        if vl.startswith("tomorrow"):
            return today + timedelta(days=1)

        explicit = re.match(r"([A-Za-z]+)\s+(\d{1,2})\s+([A-Za-z]+)", value)
        if explicit:
            day_num = explicit.group(2)
            month = explicit.group(3)
            for year in (today.year, today.year + 1):
                try:
                    parsed = datetime.strptime(
                        f"{day_num} {month} {year}", "%d %b %Y"
                    ).date()
                except ValueError:
                    continue
                if parsed >= today:
                    return parsed

        wm = re.search(r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)", value, re.IGNORECASE)
        if wm:
            target = self.WEEKDAYS[wm.group(1).lower()]
            days_ahead = (target - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return today + timedelta(days=days_ahead)

        return None
