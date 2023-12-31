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
        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        # Get the paragraph lines from the page
        data = {"bins": []}
        page_text = soup.find("div", {"class": "collect"}).find_all("p")

        # Parse the correct lines (find them, remove the ordinal indicator and make them the correct format date) and
        # then add them to the dictionary
        rubbish_day = datetime.strptime(
            remove_ordinal_indicator_from_date_string(
                page_text[2].find_next("strong").text
            ),
            "%d %B %Y",
        ).strftime(date_format)
        dict_data = {
            "type": "Rubbish",
            "collectionDate": rubbish_day,
        }
        data["bins"].append(dict_data)
        recycling_day = datetime.strptime(
            remove_ordinal_indicator_from_date_string(
                page_text[4].find_next("strong").text
            ),
            "%d %B %Y",
        ).strftime(date_format)
        dict_data = {
            "type": "Recycling",
            "collectionDate": recycling_day,
        }
        data["bins"].append(dict_data)

        return data
