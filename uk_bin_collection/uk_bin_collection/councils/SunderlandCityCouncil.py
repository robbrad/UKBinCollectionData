import re

import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

FORM_PAGE = "https://www.sunderland.gov.uk/article/12142/Find-your-bin-collection-day"
FORM_ID = "BINCOLLECTIONCHECKERNEWV3_FORM"
NEXT_TRIGGER = "BINCOLLECTIONCHECKERNEWV3_ADDRESSSEARCH_POSTCODETRIGGER"


def _form_fields(soup: BeautifulSoup) -> dict:
    form = soup.find("form", id=FORM_ID)
    return {
        inp.get("name"): inp.get("value") or ""
        for inp in form.find_all("input")
        if inp.get("name")
    }, form.get("action")


class CouncilClass(AbstractGetBinDataClass):
    """
    Sunderland City Council's bin-day checker is a GOSS iCM form. It's
    fronted by Cloudflare, but the form itself is a plain HTML postback
    wizard - no challenge is triggered by driving it directly with
    requests (session cookies + the same hidden fields/referer a real
    browser would send).
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_paon = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        check_paon(user_paon)
        check_postcode(user_postcode)
        bindata = {"bins": []}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        s = requests.Session()
        r = s.get(FORM_PAGE, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        fields, action = _form_fields(soup)
        fields["BINCOLLECTIONCHECKERNEWV3_ADDRESSSEARCH_SCCPOSTCODE"] = user_postcode
        fields["BINCOLLECTIONCHECKERNEWV3_FORMACTION_NEXT"] = NEXT_TRIGGER

        post_headers = {**headers, "Referer": FORM_PAGE}
        r = s.post(action, data=fields, headers=post_headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        select = soup.find(
            "select", id="BINCOLLECTIONCHECKERNEWV3_ADDRESSSEARCH_SCCLISTOFADDRESSES"
        )
        if not select:
            raise ValueError("No addresses found for this postcode")

        paon_upper = user_paon.strip().upper()
        match = next(
            (
                option
                for option in select.find_all("option")
                if option.get("value")
                and option.get_text(strip=True).upper().startswith(paon_upper)
            ),
            None,
        )
        if not match:
            raise ValueError(
                f"Could not match house number '{user_paon}' in address results"
            )

        fields, action = _form_fields(soup)
        fields["BINCOLLECTIONCHECKERNEWV3_ADDRESSSEARCH_SCCPOSTCODE"] = user_postcode
        fields["BINCOLLECTIONCHECKERNEWV3_ADDRESSSEARCH_SCCLISTOFADDRESSES"] = match[
            "value"
        ]
        fields["BINCOLLECTIONCHECKERNEWV3_ADDRESSSEARCH_UPRN"] = match["value"]
        fields["BINCOLLECTIONCHECKERNEWV3_ADDRESSSEARCH_POSTCODE"] = user_postcode
        fields["BINCOLLECTIONCHECKERNEWV3_ADDRESSSEARCH_ADDRESSTEXT"] = (
            match.get_text(strip=True)
        )
        fields["BINCOLLECTIONCHECKERNEWV3_FORMACTION_NEXT"] = NEXT_TRIGGER

        post_headers = {**headers, "Referer": "https://www.sunderland.gov.uk/bindays"}
        r = s.post(action, data=fields, headers=post_headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for item in soup.select(".myaccount-block__item--bin"):
            title_el = item.select_one(".myaccount-block__title")
            if not title_el:
                continue
            bin_type = title_el.get_text(strip=True)

            # The waste/recycling blocks wrap their date in a
            # "myaccount-block__date" <p>, but the Garden Waste block
            # just puts it in a plain <p> with no distinguishing
            # class, so search the whole item's text instead of a
            # specific date element.
            date_match = re.search(
                r"[A-Za-z]{3} [A-Za-z]{3} \d{1,2} \d{4}", item.get_text()
            )
            if not date_match:
                continue

            collection_date = datetime.strptime(date_match.group(), "%a %b %d %Y")
            bindata["bins"].append(
                {
                    "type": bin_type,
                    "collectionDate": collection_date.strftime(date_format),
                }
            )

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], date_format)
        )

        return bindata
