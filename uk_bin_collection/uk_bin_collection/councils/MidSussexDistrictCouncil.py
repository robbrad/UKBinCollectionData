import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def get_token_and_verification(res):
    """
    Get the UFPRT and __RequestVerificationToken codes from the form data
    :param res:
    :return: token, ufprt
    """
    soup = BeautifulSoup(res, features="html.parser")
    soup.prettify()
    ufprt = soup.find("input", {"name": "ufprt"}).get("value")
    token = soup.find("input", {"name": "__RequestVerificationToken"}).get("value")
    return token, ufprt


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        api_url = "https://www.midsussex.gov.uk/waste-recycling/bin-collection/"
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        postcode_re = "^([A-Za-z][A-Ha-hJ-Yj-y]?[0-9][A-Za-z0-9]? ?[0-9][A-Za-z]{2}|[Gg][Ii][Rr] ?0[Aa]{2})$"
        user_full_addr = f"{user_paon} {user_postcode}"

        check_postcode(user_postcode)
        check_paon(user_paon)

        # Initial request to get tokens
        session = requests.Session()
        init_res = session.get(api_url)
        token, ufprt = get_token_and_verification(init_res.text)

        form_data = {
            "__RequestVerificationToken": token,
            "ufprt": ufprt,
            "StrPostcodeSearch": user_postcode,
            "StrAddressSelect": user_full_addr,
            "Next": "true",
            "StepIndex": "1",
        }

        # First post to get updated ufprt and token
        response = session.post(api_url, data=form_data)
        token, ufprt = get_token_and_verification(response.text)
        form_data.update({"ufprt": ufprt, "__RequestVerificationToken": token})

        # Second post to retrieve collection details
        response = session.post(api_url, data=form_data)

        # Make a BS4 object
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        table_element = soup.find("table", {"class": "collDates"})
        table_rows = table_element.find_all("tr")[1:]  # skip header row

        for row in table_rows:
            details = row.find_all("td")
            dict_data = {
                "type": details[1].get_text().replace("bin collection", "").strip(),
                "collectionDate": datetime.strptime(
                    details[2].get_text(), "%A %d %B %Y"
                ).strftime("%d/%m/%Y"),
            }
            data["bins"].append(dict_data)

        # Check for Christmas changes
        christmas_heading = soup.find(
            "strong", text=re.compile("Christmas Bin Collection Calendar")
        )
        if christmas_heading:
            try:
                xmas_trs = christmas_heading.find_parent("table").find_all("tr")[1:]
            except Exception:
                return data

            for tr in xmas_trs:
                tds = tr.find_all("td")
                try:
                    normal_date = datetime.strptime(
                        tds[0].text.strip(), "%A %d %B"
                    ).date()
                    festive_date = datetime.strptime(
                        tds[1].text.strip(), "%A %d %B"
                    ).date()
                except Exception:
                    continue
                for entry in data["bins"]:
                    date = datetime.strptime(entry["collectionDate"], "%d/%m/%Y").date()
                    if date.month == normal_date.month and date.day == normal_date.day:
                        entry["collectionDate"] = festive_date.strftime("%d/%m/%Y")
                        break

        return data
