from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
import requests
from datetime import date, datetime


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # pindex isn't actually paon, it's a url parameter that I'm guessing the council use as a property id
        data = {"bins": []}
        pindex = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        check_postcode(user_postcode)

        # WBC use a url parameter called "Track" that's generated when you start a form session.
        # So first off, open the page, find the page link and copy it with the Track
        start_url = "https://wav-wrp.whitespacews.com/"
        s = requests.session()
        response = s.get(start_url)
        soup = BeautifulSoup(response.content, features="html.parser")
        soup.prettify()
        collection_page_link = soup.find_all(
            "p", {"class": "govuk-body govuk-!-margin-bottom-0 colorblue lineheight15"}
        )[0].find("a")["href"]
        track_id = collection_page_link[33:60]

        # Next we need to search using the postcode, but this is actually an important POST request
        pc_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
            "image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Origin": "https://wav-wrp.whitespacews.com",
            "Referer": "https://wav-wrp.whitespacews.com/"
            + track_id
            + "&serviceID=A&seq=2",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-GPC": "1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, "
            "like Gecko) Chrome/106.0.0.0 Safari/537.36",
        }
        form_data = {
            "address_name_number": "",
            "address_street": "",
            "street_town": "",
            "address_postcode": user_postcode,
        }
        response = s.post(
            "https://wav-wrp.whitespacews.com/mop.php?serviceID=A&"
            + track_id
            + "&seq=2",
            headers=pc_headers,
            data=form_data,
        )

        # Finally, we can use pindex to find the address and get some data
        request_url = (
            "https://wav-wrp.whitespacews.com/mop.php?"
            + track_id
            + "&serviceID=A&seq=3&pIndex="
            + pindex
        )
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
            "image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "Connection": "keep-alive",
            "Referer": "https://wav-wrp.whitespacews.com/mop.php?serviceID=A&"
            + track_id
            + "&seq=2",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-GPC": "1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, "
            "like Gecko) Chrome/106.0.0.0 Safari/537.36",
        }

        response = s.get(request_url, headers=headers)
        soup = BeautifulSoup(response.content, features="html.parser")
        soup.prettify()

        # Find the list elements
        u1_block = soup.find_all(
            "u1",
            {
                "class": "displayinlineblock justifycontentleft alignitemscenter margin0 padding0"
            },
        )

        for element in u1_block:
            x = element.find_all_next(
                "li", {"class": "displayinlineblock padding0px20px5px0px"}
            )
            dict_data = {
                "type": x[2].text.strip(),
                "collectionDate": datetime.strptime(
                    x[1].text.strip(), date_format
                ).strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
