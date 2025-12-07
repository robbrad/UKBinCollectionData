import logging

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete class for Mid-Sussex District Council implementing AbstractGetBinDataClass.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        try:
            data = {"bins": []}
            bindata = {"bins": []}
            user_paon = kwargs.get("paon")
            user_postcode = kwargs.get("postcode")
            check_postcode(user_postcode)

            URI = "https://sms-wrp.whitespacews.com/"

            session = requests.Session()

            # get link from first page as has some kind of unique hash
            r = session.get(
                URI,
            )
            r.raise_for_status()
            soup = BeautifulSoup(r.text, features="html.parser")

            alink = soup.find(
                "a",
                text="View my collections for refuse, gardening, food and recycling",
            )

            if alink is None:
                raise Exception("Initial page did not load correctly")

            # greplace 'seq' query string to skip next step
            nextpageurl = alink["href"].replace("seq=1", "seq=2")

            data = {
                "address_name_number": user_paon,
                "address_postcode": user_postcode,
            }

            # get list of addresses
            r = session.post(nextpageurl, data=data, timeout=30)
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

            u1s = soup.find("section", id="scheduled-collections").find_all(
                "ul", class_="displayinlineblock"
            )

            for u1 in u1s:
                lis = u1.find_all("li", recursive=False)

                date = lis[1].text.replace("\n", "")
                bin_type = lis[2].text.replace("\n", "")

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

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            raise
