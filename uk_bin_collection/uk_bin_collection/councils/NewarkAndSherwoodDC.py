from datetime import timedelta

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
        # Get page with BS4
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        # Work out some date bounds
        today = datetime.today()
        eight_weeks = datetime.today() + timedelta(days=8 * 7)
        data = {"bins": []}

        # Each month calendar is a table, so get the object then find all rows in that object.
        # Month and year is also a row and not included in the date, so save it then remove the row
        for month in soup.select('table[class*="table table-condensed"]'):
            info = month.find_all("tr")
            month_year = info[0].text.strip()
            info.pop(0)
            # Each remaining item is a bin collection, so get the type and tidy up the date.
            for item in info:
                bin_type = item.text.split(",")[0].strip()
                bin_date = datetime.strptime(
                    remove_ordinal_indicator_from_date_string(
                        item.text.split(",")[1].strip() + " " + month_year
                    ),
                    "%A %d %B %Y",
                )
                # Only include dates on or after today, but also only within eight weeks
                if (
                    today.date() <= bin_date.date() <= eight_weeks.date()
                    and "cancelled" not in bin_type
                ):
                    dict_data = {
                        "type": bin_type,
                        "collectionDate": bin_date.strftime(date_format),
                    }
                    data["bins"].append(dict_data)

        return data
