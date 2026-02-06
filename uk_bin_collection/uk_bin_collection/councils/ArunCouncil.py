import requests
from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

class CouncilClass(AbstractGetBinDataClass):

    def parse_data(self, page: str = None, **kwargs) -> dict:
        try:
            data = {"bins": []}

            user_postcode = kwargs.get("postcode")
            user_uprn = kwargs.get("uprn")

            check_postcode(user_postcode)
            check_uprn(user_uprn)

            BASE = "https://www1.arun.gov.uk"
            UA = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) "
                "Gecko/20100101 Firefox/146.0"
            )

            s = requests.Session()
            s.headers.update(
                {
                    "User-Agent": UA,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-GB,en;q=0.5",
                }
            )

            s.get(f"{BASE}/when-are-my-bins-collected")

            s.post(
                f"{BASE}/when-are-my-bins-collected/postcode",
                data={"postcode": user_postcode},
                headers={
                    "Referer": f"{BASE}/when-are-my-bins-collected",
                    "Origin": BASE,
                },
            )

            s.post(
                f"{BASE}/when-are-my-bins-collected/select",
                data={"address": user_uprn},
                headers={
                    "Referer": f"{BASE}/when-are-my-bins-collected/postcode",
                    "Origin": BASE,
                },
            )

            r = s.get(
                f"{BASE}/when-are-my-bins-collected/collections",
                headers={
                    "Referer": f"{BASE}/when-are-my-bins-collected/select",
                },
            )

            page = r.text


            soup = BeautifulSoup(page, "html.parser")
            soup.prettify()

            table = soup.find("table", class_="govuk-table")
            if not table:
                raise ValueError("Bin collection table not found")

            for row in table.find("tbody").find_all("tr"):
                collection_type = (
                    row.find("th", class_="govuk-table__header")
                    .text.strip()
                    .split(" ")[0]
                )

                collection_date = (
                    row.find("td", class_="govuk-table__cell")
                    .text.strip()
                )

                data["bins"].append(
                    {
                        "type": collection_type,
                        "collectionDate": collection_date,
                    }
                )

        except Exception as e:
            print(f"An error occurred: {e}")
            raise

        return data
