from bs4 import BeautifulSoup
from datetime import datetime
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

import requests
import itertools


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # Disable the SSL warnings that otherwise break everything
        requests.packages.urllib3.disable_warnings()
        requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ":HIGH:!DH:!aNULL"
        try:
            requests.packages.urllib3.contrib.pyopenssl.util.ssl_.DEFAULT_CIPHERS += (
                ":HIGH:!DH:!aNULL"
            )
        except AttributeError:
            pass

        # UPRN is street id here
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        post_url = "https://apps.castlepoint.gov.uk/cpapps/index.cfm?fa=wastecalendar.displayDetails"
        post_header_str = (
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,"
            "image/apng,"
            "*/*;q=0.8,application/signed-exchange;v=b3;q=0.9|Accept-Encoding: gzip, deflate, "
            "br|Accept-Language: en-GB;q=0.8|Cache-Control: max-age=0|Connection: "
            "keep-alive|Content-Length: "
            "11|Content-Type: application/x-www-form-urlencoded|Host: apps.castlepoint.gov.uk|Origin: "
            "https://apps.castlepoint.gov.uk|Referer: "
            "https://apps.castlepoint.gov.uk/cpapps/index.cfm?fa=wastecalendar|Sec-Fetch-Dest: "
            "document|Sec-Fetch-Mode: navigate|Sec-Fetch-Site: same-origin|Sec-Fetch-User: ?1|Sec-GPC: "
            "1|Upgrade-Insecure-Requests: 1|User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Safari/537.36 "
        )

        post_headers = parse_header(post_header_str)
        form_data = {"roadID": uprn}
        post_response = requests.post(
            post_url, headers=post_headers, data=form_data, verify=False
        )

        # Make a BS4 object
        soup = BeautifulSoup(post_response.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}
        collection_tuple = []

        for i in range(1, 3):
            calendar = soup.select(
                f"#wasteCalendarContainer > div:nth-child(2) > div:nth-child({i}) > div"
            )[0]
            month = datetime.strptime(
                calendar.find_next("h2").get_text(), "%B %Y"
            ).strftime("%m")
            year = datetime.strptime(
                calendar.find_next("h2").get_text(), "%B %Y"
            ).strftime("%Y")

            pink_days = [
                day.get_text().strip() for day in calendar.find_all("td", class_="pink")
            ]
            black_days = [
                day.get_text().strip()
                for day in calendar.find_all("td", class_="normal")
            ]

            for day in pink_days:
                collection_date = datetime(
                    year=int(year), month=int(month), day=int(day)
                )
                collection_tuple.append(("Pink collection", collection_date))

            for day in black_days:
                collection_date = datetime(
                    year=int(year), month=int(month), day=int(day)
                )
                collection_tuple.append(("Normal collection", collection_date))

        ordered_data = sorted(collection_tuple, key=lambda x: x[1])

        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        print("")
        return data
