import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        user_uprn = kwargs.get("uprn")
        check_postcode(user_postcode)

        api_base = "https://api.stratford.gov.uk/v1/addresses/postcode"
        calendar_url = "https://www.stratford.gov.uk/waste-recycling/when-we-collect.cfm/part/calendar"

        s = requests.Session()
        s.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                "Referer": "https://www.stratford.gov.uk/waste-recycling/when-we-collect.cfm",
                "Origin": "https://www.stratford.gov.uk",
            }
        )

        # Step 1: Lookup addresses by postcode via API
        postcode_stripped = user_postcode.replace(" ", "")
        params = {"national": "false", "includeNonPostal": "false"}
        r1 = s.get(f"{api_base}/{postcode_stripped}", params=params, verify=False)
        r1.raise_for_status()
        result = r1.json()

        addresses = result.get("data", [])
        if not addresses:
            raise ValueError(f"No addresses found for postcode {user_postcode}")

        # Step 2: Match address by UPRN or house number
        selected_uprn = None

        if user_uprn:
            for addr in addresses:
                if str(addr.get("uprn")) == str(user_uprn):
                    selected_uprn = str(addr["uprn"])
                    break

        if not selected_uprn and user_paon:
            paon_lower = user_paon.lower().strip()
            for addr in addresses:
                line1 = (addr.get("addressLine1") or "").lower()
                full = (addr.get("fullAddress") or "").lower()
                if line1.startswith(paon_lower) or full.startswith(paon_lower):
                    selected_uprn = str(addr["uprn"])
                    break
            if not selected_uprn:
                for addr in addresses:
                    full = (addr.get("fullAddress") or "").lower()
                    if paon_lower in full:
                        selected_uprn = str(addr["uprn"])
                        break

        if not selected_uprn:
            selected_uprn = str(addresses[0]["uprn"])

        # Step 3: POST to calendar with UPRN
        payload = {
            "frmAddress1": "",
            "frmAddress2": "",
            "frmAddress3": "",
            "frmAddress4": "",
            "frmPostcode": "",
            "frmUPRN": selected_uprn,
        }

        r2 = s.post(calendar_url, data=payload, verify=False)
        r2.raise_for_status()
        soup = BeautifulSoup(r2.text, "html.parser")

        # Step 4: Parse collection table
        table = soup.find("table", class_="table")
        if not table:
            raise ValueError("Collection table not found")

        data = {"bins": []}
        column_headers = [
            header.text.strip()
            for header in table.select("thead th.text-center strong")
        ]

        next_collection_dates = {b: None for b in column_headers}

        for row in table.select("tbody tr"):
            date_cell = row.find("td")
            if not date_cell:
                continue
            date_str = date_cell.text.strip()
            try:
                date_obj = datetime.strptime(date_str, "%A, %d/%m/%Y")
            except ValueError:
                continue

            collection_info = [
                cell.get("title", "Not Collected")
                for cell in row.select("td.text-center")
            ]

            for bin_type, status in zip(column_headers, collection_info):
                if status and status != "Not Collected":
                    if (
                        not next_collection_dates[bin_type]
                        or date_obj < next_collection_dates[bin_type]
                    ):
                        next_collection_dates[bin_type] = date_obj

        data["bins"] = [
            {"type": b, "collectionDate": d.strftime(date_format)}
            for b, d in next_collection_dates.items()
            if d is not None
        ]

        if not data["bins"]:
            raise ValueError("No collection data found")

        return data
