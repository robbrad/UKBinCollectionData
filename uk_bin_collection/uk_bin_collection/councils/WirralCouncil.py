import requests
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

        user_uprn = kwargs.get("uprn")
        bindata = {"bins": []}

        street = user_uprn.split(",")[0]
        suburb = user_uprn.split(",")[1]

        if not street:
            print("Street name could not be parsed"),
            return
        if not suburb:
            print("Street name could not be parsed"),
            return

        wastes = {
            "Non recycleable (green bin)",
            "Garden waste (brown bin)",
            "Paper and packaging (grey bin)",
        }
        DATE_REGEX = "^([0-9]{1,2} [A-Za-z]+ [0-9]{4})"

        s = requests.Session()
        # Loop through waste types
        for waste in wastes:
            r = s.get(
                f"https://ww3.wirral.gov.uk//recycling/detailContentDru7.asp?s={street}&t={suburb}&c={waste}"
            )
            # extract dates
            soup = BeautifulSoup(r.text, "html.parser")
            dates = soup.findAll("li")
            if len(dates) != 0:
                for item in dates:
                    match = re.match(DATE_REGEX, item.text)
                    if match:
                        dict_data = {
                            "type": waste,
                            "collectionDate": datetime.strptime(
                                match.group(1),
                                "%d %B %Y",
                            ).strftime("%d/%m/%Y"),
                        }
                        bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
