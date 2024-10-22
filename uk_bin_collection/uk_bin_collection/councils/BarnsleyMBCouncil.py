from typing import Dict, List, Any
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
import requests
from datetime import datetime
from uk_bin_collection.uk_bin_collection.common import (
    check_postcode,
    check_uprn,
    date_format,
)
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def parse_bin_text(bin_type_str: str, bin_date_str: str) -> List[Dict[str, str]]:
    """
    Takes a raw bin and date string, parses the bin(s) and date, then returns
    a list of bins with their date.
    """

    bins = []

    if bin_date_str == "Today":
        bin_date = datetime.today()
    elif bin_date_str == "Tomorrow":
        bin_date = datetime.today() + relativedelta(days=1)
    else:
        bin_date = datetime.strptime(bin_date_str, "%A, %B %d, %Y")

    for bin_type in bin_type_str.split(", "):
        bins.append({
            "type": bin_type.strip() + " bin",
            "collectionDate": bin_date.strftime(date_format)
        })

    return bins
    

class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs: Any) -> Dict[str, Any]:
        data: Dict[str, Any] = {"bins": []}

        # Get UPRN and postcode from kwargs
        user_uprn = str(kwargs.get("uprn"))
        user_postcode = str(kwargs.get("postcode"))
        check_postcode(user_postcode)
        check_uprn(user_uprn)

        # Pass in form data and make the POST request
        headers = {
            "authority": "waste.barnsley.gov.uk",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-GB,en;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://waste.barnsley.gov.uk",
            "pragma": "no-cache",
            "referer": "https://waste.barnsley.gov.uk/ViewCollection/SelectAddress",
            "sec-ch-ua": '"Chromium";v="118", "Opera GX";v="104", "Not=A?Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.118 Safari/537.36",
        }
        form_data = {
            "personInfo.person1.HouseNumberOrName": "",
            "personInfo.person1.Postcode": f"{user_postcode}",
            "personInfo.person1.UPRN": f"{user_uprn}",
            "person1_SelectAddress": "Select address",
        }
        response = requests.post(
            "https://waste.barnsley.gov.uk/ViewCollection/SelectAddress",
            headers=headers,
            data=form_data,
        )

        if response.status_code != 200:
            raise ConnectionRefusedError(
                "Error getting results from website! Please open an issue on GitHub!"
            )

        soup = BeautifulSoup(response.text, features="html.parser")

        results = soup.find_all("fieldset")

        # Next collection details
        highlight_content = results[0].find("div", {"class": "highlight-content"})
        bin_date_str = highlight_content.find(
            "em", {"class": "ui-bin-next-date"}
        ).text.strip()
        bin_type_str = highlight_content.find(
            "p", {"class": "ui-bin-next-type"}
        ).text.strip()

        data["bins"].extend(parse_bin_text(bin_type_str, bin_date_str))

        # Hold bins we already got from next collection, to avoid re-adding
        # from upcoming collections.
        used_bins = set(bin["type"] for bin in data["bins"])

        # Upcoming collections
        upcoming_collections = results[1].find("tbody").find_all("tr")
        for row in upcoming_collections:
            columns = row.find_all("td")
            bin_date_str = columns[0].text.strip()
            bin_type_str = columns[1].text.strip()

            # Only add to bin list if not already present.
            for bin in parse_bin_text(bin_type_str, bin_date_str):
                if bin["type"] not in used_bins:
                    data["bins"].append(bin)

                    # Add to used bins, so future collections are not re-added.
                    used_bins.add(bin["type"])

        return data
