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
            "COLLECTIONDATES": f"{user_uprn}",
        }
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.7",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Referer": "https://onlineforms.bradford.gov.uk/ufs/collectiondates.eb",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-GPC": "1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
        }
        params = {
            "ebp": "30",
            "ebd": "0",
            "ebz": "1_1713270660323",
        }
        requests.packages.urllib3.disable_warnings()
        response = requests.get(
            "https://onlineforms.bradford.gov.uk/ufs/collectiondates.eb",
            params=params,
            headers=headers,
            cookies=cookies,
        )

        # Parse response text for super speedy finding
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        # BradfordMDC site has lots of embedded tables, find the table titled 'Your next general/recycling collections are:'
        for bin in soup.find_all(attrs={"class": "CTID-FHGh1Q77-_"}):
            if bin.find_all(attrs={"class": "CTID-62bNngCB-_"}):
                bin_type = "General Waste"
                bin_colour = "Green"
                bin_date_text = bin.find(attrs={"class": "CTID-62bNngCB-_"}).get_text()
            elif bin.find_all(attrs={"class": "CTID-LHo9iO0y-_"}):
                bin_type = "Recycling Waste"
                bin_colour = "Grey"
                bin_date_text = bin.find(attrs={"class": "CTID-LHo9iO0y-_"}).get_text()
            else:
                raise ValueError(f"No bin info found in {bin_type_info[0]}")

            # Collection Date info is alongside the bin type, we got the whole line in the if/elif above
            # below strips the text off at the beginning, to get a date, though recycling is a character shorter hence the lstrip
            bin_date_info = bin_date_text[29:50].lstrip(" ")

            if contains_date(bin_date_info):
                bin_date = get_next_occurrence_from_day_month(
                    datetime.strptime(
                        bin_date_info,  # + " " + datetime.today().strftime("%Y"),
                        "%a %b %d %Y",
                    )
                ).strftime(date_format)
                # print(bin_date_info)
                # print(bin_date)
            # On exceptional collection schedule (e.g. around English Bank Holidays), date will be contained in the second stripped string
            else:
                bin_date = get_next_occurrence_from_day_month(
                    datetime.strptime(
                        bin_date_info[1] + " " + datetime.today().strftime("%Y"),
                        "%a %b %d %Y",
                    )
                ).strftime(date_format)

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
