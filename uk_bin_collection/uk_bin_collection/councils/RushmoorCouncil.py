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

        data = {"bins": []}

        collections = []
        for month in soup.find_all("div", {"class": "calendar__print"}):
            current_month_name = month.find_next("h2").text
            general_bins = month.find_all("li", {"class": "active-refuse day"})
            recycling_bins = month.find_all("li", {"class": "active-recycling day"})
            bin_list = general_bins + recycling_bins
            for bin in bin_list:
                if bin.attrs.get("class")[0] == "active-recycling":
                    bin_type = "Recycling/Glass"
                elif bin.attrs.get("class")[0] == "active-refuse":
                    bin_type = "General waste/Garden"
                bin_date = datetime.strptime(bin.text.strip().capitalize() + " " + current_month_name + " " +
                                             str(datetime.now().year), '%A %d %B %Y')
                collections.append((bin_type, bin_date))

            # It'd be really hard to deal with next year, so just get December then end
            if current_month_name == "December":
                break

        ordered_data = sorted(collections, key=lambda x: x[1])
        data = {"bins": []}
        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
