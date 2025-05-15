from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta

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
        # Add in some variables we need
        data = {"bins": []}
        collections = []
        curr_date = datetime.today()

        try:
            user_uprn = kwargs.get("uprn")
            check_uprn(user_uprn)
            url = f"https://liverpool.gov.uk/Bins/BinDatesTable?UPRN={user_uprn}"
            if not user_uprn:
                # This is a fallback for if the user stored a URL in old system. Ensures backwards compatibility.
                url = kwargs.get("url")
        except Exception as e:
            raise ValueError(f"Error getting identifier: {str(e)}")

        # Make a BS4 object
        page = requests.get(url)
        soup = BeautifulSoup(page.text, "html.parser")
        soup.prettify

        # Get all table rows on the page - enumerate gives us an index, which is handy for to keep a row count.
        # In this case, the first (0th) row is headings, so we can skip it, then parse the other data.
        for idx, row in enumerate(soup.find_all("tr")):
            if idx == 0:
                continue

            row_type = row.find("th").text.strip()
            row_data = row.find_all("td")

            # When we get the row data, we can loop through it all and parse it to datetime. Because there are no
            # years, we must add it in, then check if we need to overflow it to the following year.
            for item in row_data:
                item_text = item.text.strip()

                if item_text == "Today":
                    collections.append((row_type, curr_date))
                elif item_text == "Tomorrow":
                    collections.append((row_type, curr_date + relativedelta(days=1)))
                else:
                    bin_date = datetime.strptime(
                        remove_ordinal_indicator_from_date_string(item_text),
                        "%A, %d %B",
                    ).replace(year=curr_date.year)

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
