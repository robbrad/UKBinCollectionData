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

        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)
        check_paon(user_paon)
        bindata = {"bins": []}

        URI = "https://bnr-wrp.whitespacews.com/"

        session = requests.Session()

        # get link from first page as has some kind of unique hash
        r = session.get(
            URI,
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, features="html.parser")

        alink = soup.find("a", text="View my collections")

        if alink is None:
            raise Exception("Initial page did not load correctly")

        # greplace 'seq' query string to skip next step
        nextpageurl = alink["href"].replace("seq=1", "seq=2")

        data = {
            "address_name_number": user_paon,
            "address_postcode": user_postcode,
        }

        # get list of addresses
        r = session.post(nextpageurl, data)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, features="html.parser")

        # get first address (if you don't enter enough argument values this won't find the right address)
        alink = soup.find("div", id="property_list").find("a")

        if alink is None:
            raise Exception("Address not found")

        nextpageurl = URI + alink["href"]

        # get collection page
        r = session.get(
            nextpageurl,
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, features="html.parser")

        if soup.find("span", id="waste-hint"):
            raise Exception("No scheduled services at this address")

        uls = soup.find("section", id="scheduled-collections").find_all("ul")

        for ul in uls:
            lis = ul.find_all("li", recursive=False)

            # Skip if not enough list items
            if len(lis) < 3:
                continue

            date = lis[1].text.replace("\n", "").strip()
            bin_type = lis[2].text.replace("\n", "").strip()

            dict_data = {
                "type": bin_type,
                "collectionDate": datetime.strptime(
                    date,
                    "%d/%m/%Y",
                ).strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return bindata