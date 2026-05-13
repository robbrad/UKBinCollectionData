from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    UPRN_LOOKUP_URL = "https://swict.malvernhills.gov.uk/sw2AddressLookupWS/jaxrs/PostCode"

    def parse_data(self, page: str, **kwargs) -> dict:
        api_url = "https://swict.malvernhills.gov.uk/mhdcroundlookup/HandleSearchScreen"

        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")

        if not user_uprn and user_postcode:
            user_uprn = self._resolve_uprn(user_postcode, user_paon)

        check_uprn(user_uprn)

        form_data = {"nmalAddrtxt": "", "alAddrsel": user_uprn}

        requests.packages.urllib3.disable_warnings()
        response = requests.post(api_url, data=form_data, verify=False)

        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        table_element = soup.find("table")
        if not table_element:
            raise ValueError(
                "No results table found — UPRN may be invalid or address not in bin round records"
            )

        table_body = table_element.find("tbody")
        rows = table_body.find_all("tr")

        data = {"bins": []}

        for row in rows:
            columns = row.find_all("td")
            columns = [ele.text.strip() for ele in columns]

            thisCollection = [ele for ele in columns if ele]

            if "Not applicable" not in thisCollection[1]:
                bin_type = thisCollection[0].replace("collection", "").strip()
                date = datetime.strptime(thisCollection[1], "%A %d/%m/%Y")
                dict_data = {
                    "type": bin_type,
                    "collectionDate": date.strftime(date_format),
                }
                data["bins"].append(dict_data)

        return data

    def _resolve_uprn(self, postcode: str, house_number: str = None) -> str:
        params = {
            "simple": "T",
            "pcode": postcode,
            "authority": "MHDC",
            "historical": "false",
            "hidedummyuprn": "1",
        }
        response = requests.get(self.UPRN_LOOKUP_URL, params=params, verify=False)
        response.raise_for_status()
        results = response.json().get("jArray", [])

        if not results:
            raise ValueError(f"No addresses found for postcode {postcode}")

        if house_number:
            house_lower = house_number.lower().strip()
            for entry in results:
                addr = entry.get("Address_Short", "").lower()
                if addr.startswith(house_lower):
                    return entry["UPRN"]

        if len(results) == 1:
            return results[0]["UPRN"]

        raise ValueError(
            f"Multiple addresses found for {postcode} — provide house_number to disambiguate"
        )
