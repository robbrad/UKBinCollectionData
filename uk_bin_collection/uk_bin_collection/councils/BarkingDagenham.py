import requests
from dateutil.parser import parse

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):

    def parse_data(self, page: str = None, **kwargs) -> dict:
        try:
            data = {"bins": []}

            uprn = kwargs.get("uprn")
            check_uprn(uprn)

            url = f"https://www.lbbd.gov.uk/rest/bin/{uprn}"

            r = requests.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    ),
                    "Accept": "application/json",
                },
                timeout=30,
            )
            r.raise_for_status()

            payload = r.json()
            results = payload.get("results", [])

            for entry in results:
                bin_type = entry.get("bin_name") or entry.get("bin_type")

                # Collect all date strings
                date_strings = []

                if entry.get("nextcollection"):
                    date_strings.append(entry["nextcollection"])

                for d in entry.get("futurecollections", []):
                    date_strings.append(d)

                for date_text in date_strings:
                    try:
                        cleaned = remove_ordinal_indicator_from_date_string(date_text)
                        parsed = parse(cleaned, fuzzy=True)

                        data["bins"].append(
                            {
                                "type": bin_type,
                                "collectionDate": parsed.strftime("%d/%m/%Y"),
                            }
                        )
                    except Exception:
                        continue

        except Exception as e:
            print(f"An error occurred: {e}")
            raise

        return data
