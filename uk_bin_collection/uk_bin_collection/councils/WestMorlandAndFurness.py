import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

BASE_URL = "https://www.westmorlandandfurness.gov.uk/bins-recycling-and-street-cleaning/waste-collection-schedule"


def _resolve_uprn(postcode, uprn=None, paon=None):
    """Resolve UPRN via postcode address search if not provided."""
    if uprn:
        return str(uprn)

    if not postcode:
        raise ValueError("Provide a postcode or UPRN.")

    resp = requests.get(
        f"{BASE_URL}/find",
        params={"postcode": postcode},
        timeout=30,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    select_el = soup.find("select", {"name": "uprn"})
    if not select_el:
        raise ValueError(f"No addresses found for postcode: {postcode}")

    options = [(opt["value"], opt.text.strip()) for opt in select_el.find_all("option") if opt.get("value")]
    if not options:
        raise ValueError(f"No addresses found for postcode: {postcode}")

    if paon:
        paon_norm = str(paon).strip().upper()
        for val, text in options:
            text_upper = text.upper()
            if text_upper.startswith(paon_norm + " ") or text_upper.startswith(paon_norm + ","):
                return val
        for val, text in options:
            if paon_norm in text.upper():
                return val

    return options[0][0]


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")

        resolved_uprn = _resolve_uprn(user_postcode, uprn=user_uprn, paon=user_paon)

        bindata = {"bins": []}

        URI = f"{BASE_URL}/view/{resolved_uprn}"

        current_year = datetime.now().year
        current_month = datetime.now().month

        response = requests.get(URI)

        soup = BeautifulSoup(response.text, "html.parser")
        schedule = soup.findAll("div", {"class": "waste-collection__month"})
        for month in schedule:
            collectionmonth = datetime.strptime(month.find("h3").text, "%B")
            collectionmonth = collectionmonth.month
            collectiondays = month.findAll("li", {"class": "waste-collection__day"})
            for collectionday in collectiondays:
                day = collectionday.find(
                    "span", {"class": "waste-collection__day--day"}
                ).text.strip()
                collectiondate = datetime.strptime(day, "%d")
                collectiondate = collectiondate.replace(month=collectionmonth)
                bintype = collectionday.find(
                    "span", {"class": "waste-collection__day--type"}
                ).text.strip()

                if (current_month > 9) and (collectiondate.month < 4):
                    collectiondate = collectiondate.replace(year=(current_year + 1))
                else:
                    collectiondate = collectiondate.replace(year=current_year)

                dict_data = {
                    "type": bintype,
                    "collectionDate": collectiondate.strftime("%d/%m/%Y"),
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
