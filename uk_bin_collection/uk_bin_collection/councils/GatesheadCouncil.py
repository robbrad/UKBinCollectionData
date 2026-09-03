import json

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

FORM_PAGE = "https://www.gateshead.gov.uk/article/3150/Bin-collection-day-checker"
FORM_ID = "BINCOLLECTIONCHECKER_FORM"
NEXT_TRIGGER = "BINCOLLECTIONCHECKER_ADDRESSSEARCH_NEXTBUTTON"


def _form_fields(soup: BeautifulSoup) -> dict:
    form = soup.find("form", id=FORM_ID)
    return {
        inp.get("name"): inp.get("value") or ""
        for inp in form.find_all("input")
        if inp.get("name")
    }, form.get("action")


class CouncilClass(AbstractGetBinDataClass):
    """
    Gateshead Council's bin-day checker is a GOSS iCM form, the same
    platform as Sunderland's and Powys's - a JSONP postcode lookup plus
    a plain HTTP postback wizard. No Selenium needed.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_paon = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        check_paon(user_paon)
        check_postcode(user_postcode)
        data = {"bins": []}

        # A full, realistic browser header set (not just User-Agent) - the
        # site is fronted by Cloudflare, which scores requests on header
        # completeness/consistency alongside IP reputation. This alone
        # won't clear an IP-based block (e.g. flagged datacenter IPs like
        # CI runners), but reduces the chance of also being flagged on
        # fingerprint grounds.
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }

        s = requests.Session()
        r = s.get(FORM_PAGE, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        fields, action = _form_fields(soup)

        jsonrpc = {
            "id": 1,
            "method": "postcodeSearch",
            "params": {"provider": "", "postcode": user_postcode},
        }
        r = s.get(
            "https://www.gateshead.gov.uk/apiserver/postcode",
            params={"jsonrpc": json.dumps(jsonrpc), "callback": "cb"},
            headers=headers,
            timeout=15,
        )
        r.raise_for_status()
        body = r.text
        if body.startswith("cb(") and body.endswith(")"):
            body = body[3:-1]
        addresses = json.loads(body).get("result") or []
        if len(addresses) == 1 and "Error" in addresses[0]:
            raise ValueError(addresses[0].get("Description", "Invalid postcode"))
        if not addresses:
            raise ValueError("No addresses found for this postcode")

        paon_upper = user_paon.strip().upper()
        match = next(
            (a for a in addresses if a["line1"].strip().upper() == paon_upper),
            None,
        ) or next(
            (a for a in addresses if a["line1"].strip().upper().startswith(paon_upper)),
            None,
        )
        if not match:
            raise ValueError(
                f"Could not match house name/number '{user_paon}' in address results"
            )

        addr_text = ", ".join(
            part
            for part in (
                match["line1"],
                match["line2"],
                match["line3"],
                match["line4"],
                match["town"],
                match["postcode"],
            )
            if part
        )

        fields["BINCOLLECTIONCHECKER_ADDRESSSEARCH_ADDRESSLOOKUPPOSTCODE"] = (
            user_postcode
        )
        fields["BINCOLLECTIONCHECKER_ADDRESSSEARCH_UPRN"] = match["udprn"]
        fields["BINCOLLECTIONCHECKER_ADDRESSSEARCH_ADDRESSTEXT"] = addr_text
        fields["BINCOLLECTIONCHECKER_FORMACTION_NEXT"] = NEXT_TRIGGER

        post_headers = {**headers, "Referer": FORM_PAGE}
        r = s.post(action, data=fields, headers=post_headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        table = soup.find("table", class_="bincollections__table")
        if not table:
            raise ValueError("Could not find bin collections table in page source")

        current_year = datetime.now().year
        current_month = None

        for row in table.find_all("tr"):
            th = row.find("th")
            if th and th.get("colspan"):
                current_month = th.get_text(strip=True)
                continue

            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            day = cells[0].get_text(strip=True)
            bin_cell = cells[2]

            bin_types = [
                link.get_text(strip=True) for link in bin_cell.find_all("a")
            ] or [bin_cell.get_text(strip=True)]
            bin_types = [b for b in bin_types if b]

            if not (current_month and day):
                continue

            try:
                parsed_date = datetime.strptime(
                    f"{day} {current_month} {current_year}", "%d %B %Y"
                )
            except ValueError:
                continue

            # The site shows a rolling window that can start in the past
            # (e.g. earlier in the current month) - a date more than 6
            # months behind today is next year's, not a stale one.
            if (datetime.now() - parsed_date).days > 180:
                parsed_date = parsed_date.replace(year=current_year + 1)

            for bin_type in bin_types:
                data["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": parsed_date.strftime(date_format),
                    }
                )

        data["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], date_format)
        )
        return data
