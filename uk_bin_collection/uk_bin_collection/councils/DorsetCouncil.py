from bs4 import BeautifulSoup, element
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
        data = {"bins": []}
        collections = []

        # Parse the page and find all the result boxes
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()
        results = soup.find_all("li", {"class": "resultListItem"})

        # If the result box has a wanted string in, we can use it. Check the contents of each box and find the
        # desired text and dates
        for r in results:
            if 'Your next' in r.text:
                if type(r.contents[10]) is element.NavigableString:
                    bin_text = r.contents[10].text.split(' ')[2].title() + ' bin'
                    bin_date = datetime.strptime(remove_ordinal_indicator_from_date_string(r.contents[11].text.strip()),
                                                 "%A %d %B %Y")
                else:
                    bin_text = r.contents[11].text.split(' ')[2].title() + ' bin'
                    bin_date = datetime.strptime(remove_ordinal_indicator_from_date_string(r.contents[12].text.strip()),
                                                 "%A %d %B %Y")

                if bin_date.date() >= datetime.now().date():
                    collections.append((bin_text, bin_date))

                # Sort the text and date elements by date
                ordered_data = sorted(collections, key=lambda x: x[1])

        # Put the elements into the dictionary
        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
