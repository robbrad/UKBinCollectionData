from datetime import timedelta
from xml.etree import ElementTree

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Torridge District Council — SOAP API at collections-torridge.azurewebsites.net.

    Response changed from explicit "Mon 14 Apr" dates to relative phrases
    ("Tomorrow then every Mon", "Today then every Tue", etc.) plus an embedded
    calendar table. This parser handles the relative summary lines and falls
    back to the old explicit date format if it ever reappears.
    """

    WEEKDAYS = {
        "mon": 0, "tue": 1, "wed": 2, "thu": 3,
        "fri": 4, "sat": 5, "sun": 6,
    }

    def parse_data(self, page, **kwargs) -> dict:
        user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
        headers = {
            "User-Agent": user_agent,
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri2.org/getRoundCalendarForUPRN",
        }

        uprn = kwargs.get("uprn")
        if not uprn:
            raise ValueError("UPRN is required")

        url = "https://collections-torridge.azurewebsites.net/WebService2.asmx"
        post_data = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
            'xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
            '<soap:Body><getRoundCalendarForUPRN xmlns="http://tempuri2.org/">'
            "<council>TOR</council><UPRN>" + str(uprn) + "</UPRN>"
            "<PW>wax01653</PW>"
            "</getRoundCalendarForUPRN></soap:Body></soap:Envelope>"
        )
        requests.packages.urllib3.disable_warnings()
        resp = requests.post(url, headers=headers, data=post_data, verify=False)

        namespaces = {
            "soap": "http://schemas.xmlsoap.org/soap/envelope/",
            "a": "http://tempuri2.org/",
        }
        dom = ElementTree.fromstring(resp.text)
        result = dom.find(
            "./soap:Body"
            "/a:getRoundCalendarForUPRNResponse"
            "/a:getRoundCalendarForUPRNResult",
            namespaces,
        )
        inner_html = result.text if result is not None else ""

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

        explicit = re.match(
            r"([A-Za-z]+)\s+(\d{1,2})\s+([A-Za-z]+)", value
        )
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

        wm = re.search(
            r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)", value, re.IGNORECASE
        )
        if wm:
            target = self.WEEKDAYS[wm.group(1).lower()]
            days_ahead = (target - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return today + timedelta(days=days_ahead)

        return None
