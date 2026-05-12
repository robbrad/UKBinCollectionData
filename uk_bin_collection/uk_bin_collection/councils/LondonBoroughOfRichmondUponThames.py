import re
import html as html_unescape
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import (
    check_postcode,
    check_uprn,
    date_format,
)
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

BASE_URL = "https://www.richmond.gov.uk"
MY_RICHMOND_URL = f"{BASE_URL}/myrichmond"
MY_RICHMOND_PROPERTY_URL = f"{BASE_URL}/my_richmond"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


class CouncilClass(AbstractGetBinDataClass):
    """Richmond upon Thames bin collection scraper.

    Accepts UPRN directly (used as PID), or postcode + house number
    for a 3-step lookup: postcode -> street -> property -> waste page.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        postcode = kwargs.get("postcode")
        paon = kwargs.get("paon") or kwargs.get("number")

        if uprn:
            check_uprn(uprn)
            pid = uprn
        elif postcode and paon:
            check_postcode(postcode)
            pid = self._lookup_pid(postcode, paon)
        else:
            raise ValueError(
                "Richmond: provide UPRN, or postcode + house number/name."
            )

        target_url = f"{MY_RICHMOND_PROPERTY_URL}?pid={pid}"
        html = self._fetch(target_url)
        bindata = self._parse_waste(html)
        if not bindata["bins"]:
            raise RuntimeError("Richmond: no bins found in page HTML.")
        return bindata

    def _fetch(self, url):
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.text

    def _lookup_pid(self, postcode, paon):
        """Postcode + address -> PID via the My Richmond 3-step form flow."""
        session = requests.Session()

        # Step 1: Load postcode page to get street list + form tokens
        resp = session.get(
            f"{MY_RICHMOND_URL}?postcode={postcode}", headers=HEADERS, timeout=30
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find the street search form (has USRN select)
        usrn_select = soup.find("select", {"name": "USRN"})
        if not usrn_select:
            raise ValueError(f"No streets found for postcode {postcode}")

        # Try to match street name from paon, or use all streets
        streets = usrn_select.find_all("option")
        street_usrns = [
            (s.get("value"), s.text.strip())
            for s in streets
            if s.get("value")
        ]

        if not street_usrns:
            raise ValueError(f"No streets found for postcode {postcode}")

        paon_lower = paon.strip().lower()

        # Search each street for matching address
        for usrn, street_name in street_usrns:
            form = usrn_select.find_parent("form")
            token = form.find(
                "input", {"name": "__RequestVerificationToken"}
            ).get("value")
            ufprt = form.find("input", {"name": "ufprt"}).get("value")

            data = {
                "__RequestVerificationToken": token,
                "ufprt": ufprt,
                "USRN": usrn,
                "findproperty": "Go",
            }
            resp2 = session.post(
                f"{MY_RICHMOND_URL}?postcode={postcode}",
                data=data,
                headers=HEADERS,
                timeout=30,
                allow_redirects=True,
            )
            resp2.raise_for_status()
            soup2 = BeautifulSoup(resp2.text, "html.parser")

            uprn_select = soup2.find("select", {"name": "UPRN"})
            if not uprn_select:
                continue

            for opt in uprn_select.find_all("option"):
                val = opt.get("value", "")
                text = opt.text.strip().lower()
                if val and paon_lower in text:
                    return val

        raise ValueError(
            f"Could not find address matching '{paon}' in postcode {postcode}"
        )

    def _parse_waste(self, html):
        waste_block = self._extract_waste_block(html)
        if not waste_block:
            return {"bins": []}

        bins = []
        for h_match in re.finditer(
            r"<h4>(.*?)</h4>", waste_block, flags=re.I | re.S
        ):
            bin_name = self._clean(h_match.group(1))
            if not bin_name:
                continue

            start = h_match.end()
            next_h = re.search(r"<h4>", waste_block[start:], flags=re.I)
            section = (
                waste_block[start : start + next_h.start()]
                if next_h
                else waste_block[start:]
            )

            date_lines = []
            ul_match = re.search(
                r"<ul[^>]*>(.*?)</ul>", section, flags=re.I | re.S
            )
            if ul_match:
                for li in re.findall(
                    r"<li[^>]*>(.*?)</li>",
                    ul_match.group(1),
                    flags=re.I | re.S,
                ):
                    text = self._clean(li)
                    if text:
                        date_lines.append(text)

            if not date_lines:
                p_match = re.search(
                    r"<p[^>]*>(.*?)</p>", section, flags=re.I | re.S
                )
                if p_match:
                    text = self._clean(p_match.group(1))
                    if text:
                        date_lines.append(text)

            col_date = self._first_date(date_lines)
            if col_date:
                bins.append({"type": bin_name, "collectionDate": col_date})

        return {"bins": bins}

    def _extract_waste_block(self, html):
        m = re.search(
            r'<div[^>]+class="[^"]*my-waste[^"]*"[^>]*>(.+?)(?=<div[^>]+class="[^"]*my-item\b|</body>)',
            html,
            flags=re.I | re.S,
        )
        if m:
            return m.group(1)
        m2 = re.search(
            r'<a\s+id="my_waste"\s*></a>(.+?)(?=<a\s+id="my_parking"|<a\s+id="my_councillors")',
            html,
            flags=re.I | re.S,
        )
        if m2:
            return m2.group(1)
        return None

    def _clean(self, s):
        s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
        s = re.sub(r"<[^>]+>", "", s)
        s = html_unescape.unescape(s)
        return " ".join(s.split())

    def _first_date(self, lines):
        date_rx = re.compile(
            r"(?:(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+)?"
            r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})"
        )
        for line in lines:
            m = date_rx.search(line)
            if m:
                ds = m.group(0)
                fmt = "%A %d %B %Y" if m.group(1) else "%d %B %Y"
                dt = datetime.strptime(ds, fmt)
                return dt.strftime(date_format)
        return None
