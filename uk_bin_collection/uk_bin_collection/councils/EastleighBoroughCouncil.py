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
        uprn = kwargs.get("uprn")
        # Check the UPRN is valid
        check_uprn(uprn)

        # Request URL
        url = f"https://www.eastleigh.gov.uk/waste-bins-and-recycling/collection-dates/your-waste-bin-and-recycling-collections?uprn={uprn}"

        # Make Request
        requests.packages.urllib3.disable_warnings()
        page = requests.get(url)

        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        # Data to return
        data = {"bins": []}

        # Valid bin types
        binTypes = [
            "Household Waste Bin",
            "Recycling Bin",
            "Food Waste Bin",
            "Glass Box and Batteries",
            "Garden Waste Bin",
        ]

        # Value to create dict for DL values
        keys, values = [], []

        # Loop though DT and DD for DL containing bins
        dl = soup.find("dl", {"class": "dl-horizontal"})
        for dt in dl.find_all("dt"):
            keys.append(dt.text.strip())
        for dd in dl.find_all("dd"):
            values.append(dd.text.strip())

        # Create dict for bin name and string dates
        binDict = dict(zip(keys, values))

        # Process dict for valid bin types
        for bin in list(binDict):
            if bin in binTypes:
                if not binDict[bin].startswith("You haven't yet signed up for"):
                    # Convert date
                    date = datetime.strptime(binDict[bin], "%a, %d %b %Y")
    
                    # Set bin data
                    dict_data = {
                        "type": bin,
                        "collectionDate": date.strftime(date_format),
                    }
                    data["bins"].append(dict_data)

        # Return bin data
        return data
