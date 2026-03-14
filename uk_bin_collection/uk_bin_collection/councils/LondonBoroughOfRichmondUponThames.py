# uk_bin_collection/uk_bin_collection/councils/richmond_gov_uk.py

import re
import html as html_unescape
from datetime import datetime
from urllib.parse import urlparse, parse_qs

import requests

from uk_bin_collection.uk_bin_collection.common import date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Richmond upon Thames – parse the static My Property page.
    No Selenium. No BeautifulSoup. Just requests + regex tailored to the current markup.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        base_url = kwargs.get("url") or page
        pid_arg = kwargs.get("pid")
        paon = kwargs.get("paon")

        # work out final URL, but DO NOT add #my_waste
        pid_from_url = self._pid_from_url(base_url)
        pid_from_paon = self._pid_from_paon(paon)

        if "pid=" in (base_url or ""):
            target_url = base_url
        elif pid_arg or pid_from_paon:
            pid = pid_arg or pid_from_paon
            sep = "&" if "?" in (base_url or "") else "?"
            target_url = f"{base_url}{sep}pid={pid}"
        else:
            raise ValueError(
                "Richmond: supply a URL that already has ?pid=... OR put PID in the House Number field."
            )

        html = self._fetch_html(target_url)
        bindata = self._parse_html_for_waste(html)
        if not bindata["bins"]:
            raise RuntimeError("Richmond: no bins found in page HTML.")
        return bindata

    # ----------------- HTTP -----------------

    def _fetch_html(self, url: str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.text

    # ----------------- parsing (regex) -----------------

    def _parse_html_for_waste(self, html: str) -> dict:
        # isolate the waste block between <a id="my_waste"> and next section
        waste_block = self._extract_waste_block(html)
        if not waste_block:
            return {"bins": []}

        bins = []

        # find all <h4>...</h4> in that block
        for h_match in re.finditer(r"<h4>(.*?)</h4>", waste_block, flags=re.I | re.S):
            bin_name = self._clean(h_match.group(1))
            if not bin_name:
                continue

            # slice from end of this <h4> to either next <h4> or end of block
            start = h_match.end()
            # find next h4 after this one
            next_h = re.search(r"<h4>", waste_block[start:], flags=re.I)
            if next_h:
                section = waste_block[start : start + next_h.start()]
            else:
                section = waste_block[start:]

            # try to find <ul> ... <li>...</li> ... </ul>
            date_lines = []
            ul_match = re.search(r"<ul[^>]*>(.*?)</ul>", section, flags=re.I | re.S)
            if ul_match:
                ul_inner = ul_match.group(1)
                for li in re.findall(r"<li[^>]*>(.*?)</li>", ul_inner, flags=re.I | re.S):
                    text = self._clean(li)
                    if text:
                        date_lines.append(text)

            # fallback to <p>...</p>
            if not date_lines:
                p_match = re.search(r"<p[^>]*>(.*?)</p>", section, flags=re.I | re.S)
                if p_match:
                    text = self._clean(p_match.group(1))
                    if text:
                        date_lines.append(text)

            col_date = self._first_date_or_message(date_lines)
            if col_date:
                bins.append(
                    {
                        "type": bin_name,
                        "collectionDate": col_date,
                    }
                )

        return {"bins": bins}

    def _extract_waste_block(self, html: str) -> str | None:
        # try to grab from <a id="my_waste"> to <a id="my_parking"> (or my-councillors as fallback)
        m = re.search(
            r'<a\s+id=["\']my_waste["\']\s*></a>(.+?)(?:<a\s+id=["\']my_parking["\']|<a\s+id=["\']my_councillors["\'])',
            html,
            flags=re.I | re.S,
        )
        if not m:
            return None
        return m.group(1)

    # ----------------- small helpers -----------------

    def _pid_from_url(self, url: str | None) -> str | None:
        if not url:
            return None
        try:
            q = parse_qs(urlparse(url).query)
            return q.get("pid", [None])[0]
        except Exception:
            return None

    def _pid_from_paon(self, paon) -> str | None:
        # allow putting PID into "house number"
        if paon and str(paon).isdigit() and 10 <= len(str(paon)) <= 14:
            return str(paon)
        return None

    def _clean(self, s: str) -> str:
        # remove tags, unescape, strip
        # first remove <br> and friends by replacing with space
        s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
        # strip any other simple tags
        s = re.sub(r"<[^>]+>", "", s)
        s = html_unescape.unescape(s)
        return " ".join(s.split())

    def _first_date_or_message(self, lines) -> str | None:
        # match "Thursday 23 October 2025" or "23 October 2025"
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

            lower = line.lower()
            if "no collection" in lower or "no contract" in lower or "no subscription" in lower:
                return line
        return None
