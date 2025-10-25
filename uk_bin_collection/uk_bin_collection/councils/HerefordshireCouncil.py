import logging

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
        try:
            user_uprn = kwargs.get("uprn")
            check_uprn(user_uprn)
            url = f"https://www.herefordshire.gov.uk/rubbish-recycling/check-bin-collection-day?blpu_uprn={user_uprn}"
            if not user_uprn:
                # This is a fallback for if the user stored a URL in old system. Ensures backwards compatibility.
                url = kwargs.get("url")
        except Exception as e:
            raise ValueError(f"Error getting identifier: {str(e)}")

        # Make a BS4 object
        page = requests.get(url)
        soup = BeautifulSoup(page.text, "html.parser")
        soup.prettify

        checkValid = any("Your next collection days" in h2.get_text() for h2 in soup.find_all("h2"))
        if checkValid is None:
            raise ValueError("Address/UPRN not found")

        data = {"bins": []}

        for h3 in soup.find_all("h3", class_="c-supplement__heading"):
            bin_type = h3.get_text(strip=True)

            # Skip unrelated items
            if "bin" not in bin_type.lower():
                continue

            # The <ul> immediately following contains the collection dates
            ul = h3.find_next_sibling("ul")
            if not ul:
                continue

            # Get the first <li>, which is the 'next collection' entry
            next_date = ul.find("li").get_text(strip=True).replace(" (next collection)", "")

            logging.info(f"Bin type: {bin_type} - Collection date: {next_date}")

            data["bins"].append(
                {
                    "type": bin_type,
                    "collectionDate": datetime.strptime(next_date, "%A %d %B %Y").strftime(date_format),
                }
            )

        return data
