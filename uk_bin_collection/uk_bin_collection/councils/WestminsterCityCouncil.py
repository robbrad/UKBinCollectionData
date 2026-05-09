import logging
import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import check_usrn, date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

_LOGGER = logging.getLogger(__name__)

# Westminster's transact subdomain redirects HTTP -> HTTPS via 301; following
# that redirect on a POST converts it to a GET (RFC 7231) and silently drops
# the form body. Always hit HTTPS directly.
LOOKUP_URL = "https://transact.westminster.gov.uk/env/streetsearch.aspx"

DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_INDEX = {abbr: i for i, abbr in enumerate(DAY_ORDER)}


class CouncilClass(AbstractGetBinDataClass):
    """
    Westminster City Council uses a street-based ASP.NET WebForms lookup at
    transact.westminster.gov.uk/env/streetsearch.aspx. The dropdown's option
    values are USRNs (Unique Street Reference Numbers); pass the USRN via the
    `usrn` kwarg.

    The response renders three tables:
      1. General bin presentation/collection windows (per-street).
      2. Service-specific collections (Recycling, Food Recycling, etc).
      3. Street cleaning schedule -- skipped because it is not a bin service.

    Westminster's data is recurring weekday windows rather than calendar
    dates, so for each row we report the next occurrence of the listed
    day(s).
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        usrn = kwargs.get("usrn")
        check_usrn(usrn)

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                )
            }
        )

        get_resp = session.get(LOOKUP_URL, timeout=60)
        get_resp.raise_for_status()
        form_soup = BeautifulSoup(get_resp.text, "html.parser")

        post_data = {
            "__VIEWSTATE": _hidden(form_soup, "__VIEWSTATE"),
            "__VIEWSTATEGENERATOR": _hidden(form_soup, "__VIEWSTATEGENERATOR"),
            "__EVENTVALIDATION": _hidden(form_soup, "__EVENTVALIDATION"),
            "dlstreets": str(usrn),
            "btnsearch": _btn_value(form_soup),
        }

        post_resp = session.post(
            LOOKUP_URL,
            data=post_data,
            headers={
                "Referer": LOOKUP_URL,
                "Origin": "https://transact.westminster.gov.uk",
            },
            timeout=60,
        )
        post_resp.raise_for_status()

        result_soup = BeautifulSoup(post_resp.text, "html.parser")
        return _build_bins(result_soup)


def _hidden(soup, name):
    el = soup.find("input", {"name": name})
    if not el:
        raise ValueError(f"Westminster page missing hidden field: {name}")
    return el.get("value", "")


def _btn_value(soup):
    btn = soup.find("input", {"name": "btnsearch"})
    return btn.get("value", "") if btn else ""


def _expand_days(text):
    """Expand 'Mon - Fri' / 'Sat, Sun' / 'Fri' into a list of 3-letter abbrs."""
    text = text.strip()
    if not text:
        return []
    if "-" in text:
        parts = [p.strip()[:3] for p in text.split("-")]
        if len(parts) == 2 and parts[0] in DAY_INDEX and parts[1] in DAY_INDEX:
            return DAY_ORDER[DAY_INDEX[parts[0]] : DAY_INDEX[parts[1]] + 1]
    out = []
    for token in re.split(r"[,&]", text):
        token = token.strip()[:3]
        if token in DAY_INDEX:
            out.append(token)
    return out


def _next_date_for_day(day_abbr, today):
    target = DAY_INDEX[day_abbr]
    days_ahead = (target - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return (today + timedelta(days=days_ahead)).strftime(date_format)


def _build_bins(soup):
    bins = []
    seen = set()
    today = datetime.now()

    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if not headers:
            continue
        if "swept" in table.get_text(" ", strip=True).lower():
            continue
        has_service_column = any("service description" in h.lower() for h in headers)

        for row in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
            if not cells:
                continue

            if has_service_column:
                # [Location, Service, '', Week Days, Week Times, Weekend Days, Weekend Times]
                if len(cells) < 4:
                    continue
                service = cells[1]
                if not service or "swept" in service.lower():
                    continue
                bin_type = service
                day_cells = cells[2:]
            else:
                # [Location, Week Days, Week Times, Weekend Days, Weekend Times]
                bin_type = "General Waste Collection"
                day_cells = cells[1:]

            days = []
            for cell in day_cells:
                if re.search(r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b", cell):
                    days.extend(_expand_days(cell))

            if not days:
                continue

            next_dates = sorted({_next_date_for_day(d, today) for d in days})
            collection_date = next_dates[0]

            key = (bin_type, collection_date)
            if key in seen:
                continue
            seen.add(key)

            bins.append({"type": bin_type, "collectionDate": collection_date})

    bins.sort(key=lambda b: datetime.strptime(b["collectionDate"], date_format))
    return {"bins": bins}
