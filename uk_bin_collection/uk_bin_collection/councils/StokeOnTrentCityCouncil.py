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
        soup = BeautifulSoup(page.text, features="lxml-xml")
        soup.prettify()

        data = {"bins": []}
        collections = []

        # Match bin types from API to their actual type
        bin_types = {
            "RESIDUAL BIN": "Grey bin",
            "RES 180": "Grey bin",
            "RES 240 STD": "Grey bin",
            "RES 360 STD+": "Grey bin",
            "RES 360 STD": "Grey bin",
            "RES 660": "Grey bin",
            "RES 770": "Grey bin",
            "RES BAG": "Grey bin",
            "RES 140 SML": "Grey bin",
            "REC 180 SML": "Blue bin",
            "REC 240 STD": "Blue bin",
            "REC 360": "Blue bin",
            "REC 770": "Blue bin",
            "MIXED REC 55 BOX": "Blue box",
            "PAPER 44 BOX": "Blue box",
            "PAPER BAG": "Paper bag",
            "ORG 180": "Brown bin",
            "ORG 240 STD": "Brown bin",
            "PAID ORGANIC": "Brown bin",
            "RES 1100": "Grey trade container",
            "REC GL 770": "Blue trade container",
        }
        # If the API errors, throw the exception
        if soup.find("Error") is not None:
            raise ConnectionAbortedError(soup.find("Error").text.strip())

        # Parse the XML and add to a list of collections
        for item in soup.find_all("BinRound"):
            try:
                bin_type = bin_types.get(
                    item.find_next("Bin").text.replace("EMPTY BINS", "").strip()
                )
                bin_date = datetime.strptime(
                    item.find_next("DateTime").text, "%d/%m/%Y %H:%M:%S"
                )
                if bin_date >= datetime.now():
                    collections.append((bin_type, bin_date))
            except:
                raise SystemError(
                    "Error has been encountered parsing API. Please try again later and if the issue "
                    "persists, open a GitHub ticket!"
                )

        # Sort the collections list by date
        ordered_data = sorted(collections, key=lambda x: x[1])

        # Put the elements into the dictionary
        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
