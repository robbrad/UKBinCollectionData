import re
import html as html_unescape
from datetime import datetime
from urllib.parse import urlparse, parse_qs

import requests

from uk_bin_collection.uk_bin_collection.common import date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """Richmond upon Thames – parse My Richmond property page."""

    def parse_data(self, page: str, **kwargs) -> dict:
        base_url = kwargs.get("url") or page
        paon = kwargs.get("paon")

        pid = self._pid_from_url(base_url) or self._pid_from_paon(paon)
        if not pid:
            raise ValueError(
                "Richmond: supply a URL with ?pid=... OR put PID in the House Number field."
            )

        if "pid=" not in (base_url or ""):
            sep = "&" if "?" in (base_url or "") else "?"
            target_url = f"{base_url}{sep}pid={pid}"
        else:
            target_url = base_url

        html = self._fetch_html(target_url)
        bindata = self._parse_html_for_waste(html)
        if not bindata["bins"]:
            raise RuntimeError("Richmond: no bins found in page HTML.")
        return bindata

    def _fetch_html(self, url):
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.text

    def _parse_html_for_waste(self, html):
        waste_block = self._extract_waste_block(html)
        if not waste_block:
            return {"bins": []}

        bins = []
        for h_match in re.finditer(r"<h4>(.*?)</h4>", waste_block, flags=re.I | re.S):
            bin_name = self._clean(h_match.group(1))
            if not bin_name:
                continue

            start = h_match.end()
            next_h = re.search(r"<h4>", waste_block[start:], flags=re.I)
            section = waste_block[start:start + next_h.start()] if next_h else waste_block[start:]

            date_lines = []
            ul_match = re.search(r"<ul[^>]*>(.*?)</ul>", section, flags=re.I | re.S)
            if ul_match:
                for li in re.findall(r"<li[^>]*>(.*?)</li>", ul_match.group(1), flags=re.I | re.S):
                    text = self._clean(li)
                    if text:
                        date_lines.append(text)

            if not date_lines:
                p_match = re.search(r"<p[^>]*>(.*?)</p>", section, flags=re.I | re.S)
                if p_match:
                    text = self._clean(p_match.group(1))
                    if text:
                        date_lines.append(text)

            col_date = self._first_date(date_lines)
            if col_date:
                bins.append({"type": bin_name, "collectionDate": col_date})

        return {"bins": bins}

    def _extract_waste_block(self, html):
        # New format: <div class="my-item my-waste">...</div>
        m = re.search(
            r'<div[^>]+class="[^"]*my-waste[^"]*"[^>]*>(.+?)(?=<div[^>]+class="[^"]*my-item\b|</body>)',
            html, flags=re.I | re.S,
        )
        if m:
            return m.group(1)
        # Old format: <a id="my_waste">
        m2 = re.search(
            r'<a\s+id="my_waste"\s*></a>(.+?)(?=<a\s+id="my_parking"|<a\s+id="my_councillors")',
            html, flags=re.I | re.S,
        )
        if m2:
            return m2.group(1)
        return None

    def _pid_from_url(self, url):
        if not url:
            return None
        try:
            q = parse_qs(urlparse(url).query)
            return q.get("pid", [None])[0]
        except Exception:
            return None

    def _pid_from_paon(self, paon):
        if paon and str(paon).isdigit() and 10 <= len(str(paon)) <= 14:
            return str(paon)
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
