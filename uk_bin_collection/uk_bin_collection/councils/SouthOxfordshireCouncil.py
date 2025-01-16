import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        # UPRN is passed in via a cookie. Set cookies/params and GET the page
        cookies = {
            # 'JSESSIONID': '96F2A15C14569B2ED2BBEB140FE86532',
            "SVBINZONE": f"SOUTH%3AUPRN%40{user_uprn}",
        }
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.7",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Referer": "https://eform.southoxon.gov.uk/ebase/BINZONE_DESKTOP.eb?SOVA_TAG=SOUTH&ebd=0&ebz=1_1668467255368",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-GPC": "1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
        }
        params = {
            "SOVA_TAG": "SOUTH",
            "ebd": "0",
            # 'ebz':      '1_1668467255368',
        }
        requests.packages.urllib3.disable_warnings()
        response = requests.get(
            "https://eform.southoxon.gov.uk/ebase/BINZONE_DESKTOP.eb",
            params=params,
            headers=headers,
            cookies=cookies,
        )

        # Parse response text for super speedy finding
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        # Page has slider info side by side, which are two instances of this class
        for bin in soup.find_all("div", {"class": "binextra"}):
            bin_info = list(bin.stripped_strings)
            try:
                # On standard collection schedule, date will be contained in the first stripped string
                if contains_date(bin_info[0]):
                    bin_date = get_next_occurrence_from_day_month(
                        datetime.strptime(
                            bin_info[0] + " " + datetime.today().strftime("%Y"),
                            "%A %d %B - %Y",
                        )
                    ).strftime(date_format)
                    bin_type = str.capitalize(" ".join(bin_info[1:]))
                # On exceptional collection schedule (e.g. around English Bank Holidays), date will be contained in the second stripped string
                else:
                    bin_date = get_next_occurrence_from_day_month(
                        datetime.strptime(
                            bin_info[1] + " " + datetime.today().strftime("%Y"),
                            "%A %d %B - %Y",
                        )
                    ).strftime(date_format)
                    str.capitalize(" ".join(bin_info[2:]))
            except:
                continue

            # Build data dict for each entry
            dict_data = {
                "type": bin_type,
                "collectionDate": bin_date,
            }
            data["bins"].append(dict_data)

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
