from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

BASE_URL = "https://myvale.valeofglamorgan.gov.uk/getdata.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-GB,en;q=0.6",
    "Referer": "https://www.valeofglamorgan.gov.uk/",
}


def _match_address(results, uprn=None, paon=None):
    """Match an address from LocationSearch results by UPRN or house number/name.
    Each result is [UniqueId, Parent, DisplayName, Type, X, Y, Rank, Name, Zoom]."""
    if uprn:
        uprn_str = str(uprn)
        for row in results:
            if str(row[0]) == uprn_str:
                return str(row[0])

    if paon:
        paon_norm = str(paon).strip().upper()
        for row in results:
            name = str(row[7]).upper()
            if name.startswith(paon_norm + " ") or name.startswith(paon_norm + ","):
                return str(row[0])
        for row in results:
            name = str(row[7]).upper()
            if paon_norm in name:
                return str(row[0])

    return str(results[0][0])


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        requests.packages.urllib3.disable_warnings()
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")

        if not user_uprn and user_postcode:
            params = {
                "RequestType": "LocationSearch",
                "location": user_postcode,
                "pagesize": "20",
                "startnum": "1",
                "gettotals": "false",
                "type": "json",
            }
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            search_data = resp.json()

            results = search_data.get("data", [])
            if not results:
                raise ValueError(f"No addresses found for postcode: {user_postcode}")

            user_uprn = _match_address(results, paon=user_paon)

        if not user_uprn:
            raise ValueError("Could not resolve address. Provide a postcode or UPRN.")

        params = {
            "RequestType": "LocalInfo",
            "ms": "ValeOfGlamorgan/AllMaps",
            "group": "Waste|new_refuse",
            "type": "jsonp",
            "callback": "AddressInfoCallback",
            "uid": user_uprn,
        }

        response = requests.get(BASE_URL, params=params, headers=HEADERS).text
        response = response.replace("AddressInfoCallback(", "").rstrip(");")

        parsed = json.loads(response)
        waste = parsed["Results"]["waste"]
        bin_week = str(waste["roundday_residual"]).replace(" ", "-")
        weekly_collection = str(waste["recycling_code"]).capitalize()
        weekly_dates = get_weekday_dates_in_period(
            datetime.now(), days_of_week.get(bin_week.split("-")[0].strip()), amount=48
        )
        schedule_url = f"https://www.valeofglamorgan.gov.uk/en/living/Recycling-and-Waste/collections/Black-Bag-Collections/{bin_week}.aspx"
        response = requests.get(schedule_url, verify=False, headers=HEADERS)

        soup = BeautifulSoup(response.text, features="html.parser")

        collections = []

        table = soup.find("table", {"class": "TableStyle_Activities"}).find("tbody")
        for tr in soup.find_all("tr")[1:]:
            row = tr.find_all("td")
            month_and_year = row[0].text.split()
            if month_and_year[0] in list(calendar.month_abbr):
                collection_month = datetime.strptime(month_and_year[0], "%b").month
            elif month_and_year[0] == "Sept":
                collection_month = int(9)
            else:
                collection_month = datetime.strptime(month_and_year[0], "%B").month
            collection_year = datetime.strptime(month_and_year[1], "%Y").year

            for day in remove_alpha_characters(row[1].text.strip()).split():
                try:
                    bin_date = datetime(collection_year, collection_month, int(day))
                    table_headers = table.find("tr").find_all("th")
                    collections.append(
                        (
                            table_headers[1]
                            .text.strip()
                            .replace(" collection date", ""),
                            bin_date,
                        )
                    )
                except Exception:
                    continue

        for date in weekly_dates:
            collections.append(
                (weekly_collection, datetime.strptime(date, date_format))
            )

        ordered_data = sorted(collections, key=lambda x: x[1])
        data = {"bins": []}
        for item in ordered_data:
            collection_date = item[1]
            if collection_date.date() >= datetime.now().date():
                dict_data = {
                    "type": item[0],
                    "collectionDate": collection_date.strftime(date_format),
                }
                data["bins"].append(dict_data)

        return data
