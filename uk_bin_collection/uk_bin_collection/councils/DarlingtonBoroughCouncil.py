import re

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

        data = {"bins": []}

        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        url = f"https://www.darlington.gov.uk/bins-waste-and-recycling/collection-day-lookup/?uprn={user_uprn}"

        # Referrer: https://www.darlington.gov.uk/bins-waste-and-recycling/collection-day-lookup/
        # X-Requested-With: XMLHttpRequest
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-GB,en;q=0.5",
            "Referer": "https://www.darlington.gov.uk/bins-waste-and-recycling/collection-day-lookup/",
            "Sec-Detch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.186 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }

        # Make a BS4 object
        page = requests.get(url, headers=headers)
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        # Loop over each date card
        card_blocks = soup.select("#detailsDisplay .refuse-results")

        for card in card_blocks:
            bin_date_tag = card.select_one(".card-footer h3")
            if not bin_date_tag:
                continue

            bin_type = card.select_one(".card-header h2").text.strip()
            bin_date = bin_date_tag.text.strip()

            # Remove any extra text from the date "(Today)", "(Tomorrow)"
            cleaned_bin_date = re.sub(r"\s*\(.*?\)", "", bin_date).strip()

            next_binfo = {
                "type": bin_type,
                "collectionDate": datetime.strptime(
                    cleaned_bin_date, "%A %d %B %Y"
                ).strftime(date_format),
            }

            data["bins"].append(next_binfo)

        return data
