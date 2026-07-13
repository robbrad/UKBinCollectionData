import re

from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
from dateutil.relativedelta import relativedelta
from datetime import timedelta


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}

        # response = requests.get('https://www.rochford.gov.uk/online-bin-collections-calendar', headers=headers)
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()
        year = soup.find_all("table", {"class": "responsive-enabled govuk-table"})

        current_month = datetime.now().strftime("%B %Y")
        next_month = (datetime.now() + relativedelta(months=1, day=1)).strftime("%B %Y")

        for month in year:
            heading = (
                month.find("th", {"class": "govuk-table__header"}).get_text().strip()
            )
            if heading == current_month or heading == next_month:
                for week in month.find("tbody").find_all(
                    "tr", {"class": "govuk-table__row"}
                ):
                    week_text = week.get_text().strip().split("\n")
                    # The site publishes a date *range* for the collection
                    # week (e.g. "Monday 6th July - Friday 10th July"), not
                    # the resident's actual collection day. Take the last
                    # (latest) date in the range rather than the first, so a
                    # week isn't treated as "already passed" - and therefore
                    # skipped ahead to the next occurrence - as soon as its
                    # Monday goes by, even though the real collection day
                    # (any day up to Friday) hasn't happened yet.
                    date_parts = re.split(r"\s*[-–�]\s*", week_text[0])
                    date_str = date_parts[-1].strip()
                    collection_date = datetime.strptime(
                        remove_ordinal_indicator_from_date_string(date_str),
                        "%A %d %B",
                    )
                    next_collection = collection_date.replace(year=datetime.now().year)
                    if datetime.now().month == 12 and next_collection.month == 1:
                        next_collection = next_collection + relativedelta(years=1)
                    bin_type = (
                        week_text[1]
                        .replace("collection week", "bin")
                        .strip()
                        .capitalize()
                    )
                    if next_collection.date() >= (datetime.now().date() - timedelta(6)):
                        dict_data = {
                            "type": bin_type,
                            "collectionDate": next_collection.strftime(date_format),
                        }
                        data["bins"].append(dict_data)
            else:
                continue

        return data
