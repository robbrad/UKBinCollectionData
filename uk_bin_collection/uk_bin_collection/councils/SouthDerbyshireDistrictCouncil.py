import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

SEARCH_URL = "https://maps.southderbyshire.gov.uk/iShareLIVE.web/getdata.aspx"
BIN_URL = "https://maps.southderbyshire.gov.uk/iShareLIVE.web//getdata.aspx"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


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
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")

        requests.packages.urllib3.disable_warnings()

        if not user_uprn and user_postcode:
            params = {
                "RequestType": "LocationSearch",
                "location": user_postcode,
                "pagesize": "20",
                "startnum": "1",
                "gettotals": "false",
                "type": "json",
            }
            resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, verify=False, timeout=30)
            resp.raise_for_status()
            search_data = resp.json()

            results = search_data.get("data", [])
            if not results:
                raise ValueError(f"No addresses found for postcode: {user_postcode}")

            user_uprn = _match_address(results, paon=user_paon)

        if not user_uprn:
            raise ValueError("Could not resolve address. Provide a postcode or UPRN.")

        url = f"{BIN_URL}?RequestType=LocalInfo&ms=mapsources/MyHouse&format=JSONP&group=Recycling%20Bins%20and%20Waste|Next%20Bin%20Collections&uid={user_uprn}"
        response = requests.get(url, verify=False, headers=HEADERS, timeout=30).text

        data = {"bins": []}
        jsonp_pattern = r"import\((\{.*\})\)"
        json_match = re.search(jsonp_pattern, response, re.S)

        if json_match:
            json_data = json_match.group(1)
            parsed_data = json.loads(json_data)
            html_content = parsed_data["Results"]["Next_Bin_Collections"]["_"]

            matches = re.findall(
                r"<span.*?>(\d{2} \w+ \d{4})</span>.*?<span.*?>(.*?)</span>",
                html_content,
                re.S,
            )

            for match in matches:
                dict_data = {
                    "type": match[1],
                    "collectionDate": datetime.strptime(
                        match[0], "%d %B %Y"
                    ).strftime("%d/%m/%Y"),
                }
                data["bins"].append(dict_data)

        return data
