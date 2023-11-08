from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass
from dateutil.relativedelta import relativedelta


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        collections = []
        curr_date = datetime.today()
        for idx, row in enumerate(soup.find_all("tr")):
            if idx == 0:
                continue
            row_type = row.find("th").text.strip()
            row_data = row.find_all("td")
            for item in row_data:
                if item.text.strip() == "Today":
                    collections.append((row_type, curr_date))
                else:
                    bin_date = datetime.strptime(remove_ordinal_indicator_from_date_string(item.text.strip()),
                                                 "%A, %d %B").replace(year=curr_date.year)
                    if curr_date.month == 12 and bin_date.month == 1:
                        bin_date = bin_date + relativedelta(years=1)
                    collections.append((row_type, bin_date))

        # Sort the text and list elements by date
        ordered_data = sorted(collections, key=lambda x: x[1])

        # Put the elements into the dictionary
        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
