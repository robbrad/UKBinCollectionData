# This script pulls (in one hit) the data
# from Warick District Council Bins Data
from bs4 import BeautifulSoup
from get_bin_data import AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the base
    class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page) -> None:
        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        for bins in soup.findAll("div", {"class": lambda L: L
                                         and L.startswith('mb10 ind-waste-')}):

            # Get the type of bin
            binTypes = bins.find_all("div", {"class": 'mb10'})
            binType = binTypes[0].get_text(strip=True)

            # Find the collection dates
            binCollections = bins.find_all("div", {"class": lambda L: L
                                                   and L.startswith('col-sm-4')
                                                   })

            if binCollections:
                lastCollections = binCollections[0].find_all("div")
                nextCollections = binCollections[1].find_all("div")

                # Get the collection date
                lastCollection = lastCollections[1].get_text(strip=True)
                nextCollection = nextCollections[1].get_text(strip=True)

                if lastCollection:
                    dict_data = {
                     "BinType": binType,
                     "Last Collection Date": lastCollection,
                     "Next Collection Date": nextCollection
                    }

                    data["bins"].append(dict_data)

        return data
