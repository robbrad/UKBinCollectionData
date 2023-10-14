# This script pulls (in one hit) the data from Bromley Council Bins Data
import datetime
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


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

        bin_data_dict = {"bins": []}
        collections = []


        # Search for the specific bins in the table using BS4
        bin_types = soup.find_all("h3", class_="govuk-heading-m waste-service-name")
        collection_info = soup.find_all("dl", {"class": "govuk-summary-list"})

        # Raise error if data is not loaded at time of scrape (30% chance it is)
        if len(bin_types) == 0:
            raise ConnectionError("Error fetching council data: data absent when page was scraped.")

        # Parse the data
        for idx, value in enumerate(collection_info):
            bin_type = bin_types[idx].text.strip()
            collection_date = value.contents[3].contents[3].text.strip()
            next_collection = datetime.strptime(remove_ordinal_indicator_from_date_string(collection_date.replace(',', '')), "%A %d %B")
            curr_date = datetime.now().date()
            next_collection = next_collection.replace(year=curr_date.year)
            if curr_date.month == 12 and next_collection.month == 1:
                next_collection = next_collection + relativedelta(years=1)
            collections.append((bin_type, next_collection))

        # Sort the text and list elements by date
        ordered_data = sorted(collections, key=lambda x: x[1])

        # Put the elements into the dictionary
        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            bin_data_dict["bins"].append(dict_data)


        return bin_data_dict
