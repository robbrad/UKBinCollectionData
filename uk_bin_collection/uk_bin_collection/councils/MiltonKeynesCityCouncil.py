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

        # Get the estate from the UPRN field
        estate = kwargs.get('uprn')

        # Parse the council's website
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        # Get a list of lists of estates and their collection days, then check for a match on estate name
        collection_days = [item.text.strip().replace(u'\xa0', u' ').split(' - ') for item in soup.find("div", {"class": "field field--name-localgov-paragraphs field--type-entity-reference-revisions field--label-hidden field__items"}).find_all("li")]
        result = [result for result in collection_days if result[0].lower() == estate.lower()]

        # If there is a match, we can process it by getting the next eight dates for that day. Else, raise an exception.
        if result is not None:
            day_number = days_of_week.get(result[0][1].split()[0])
            collection_dates = get_weekday_dates_in_period(datetime.now(), day_number, 8)

            for date in collection_dates:
                dict_data = {
                    "type":           f'Weekly collection',
                    "collectionDate": date,
                }
                data["bins"].append(dict_data)
        else:
            raise ValueError("Estate not found on website.")

        return data
