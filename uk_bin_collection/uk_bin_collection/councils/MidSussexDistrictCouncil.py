import logging

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

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

            # The council previously used the shared Whitespace portal at
            # sms-wrp.whitespacews.com. That subdomain now returns
            # "Access denied!" — the council moved to a self-branded
            # Whitespace deployment at waste.services.midsussex.gov.uk
            # but the underlying flow (seq=1 -> seq=2 with paon/postcode)
            # is identical.
            URI = "https://waste.services.midsussex.gov.uk/"

            session = requests.Session()
            session.headers.update(
                {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/132.0.0.0 Safari/537.36"
                    )
                }
            )

            # get link from first page as has some kind of unique hash
            r = session.get(URI, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, features="html.parser")

            alink = soup.find(
                "a",
                string=lambda s: s
                and "View my collections" in s,
            )

            if alink is None:
                raise Exception("Initial page did not load correctly")

            # replace 'seq' query string to skip next step
            nextpageurl = alink["href"].replace("seq=1", "seq=2")

            data = {
                "address_name_number": user_paon,
                "address_postcode": user_postcode,
            }

            r = session.post(nextpageurl, data=data, timeout=30)
            r.raise_for_status()

            soup = BeautifulSoup(r.text, features="html.parser")

            alink = soup.find("div", id="property_list").find("a")

            if alink is None:
                raise Exception("Address not found")

            # property_list href may already be absolute on the rebranded portal
            href = alink["href"]
            if href.startswith("http"):
                nextpageurl = href
            else:
                nextpageurl = URI + href.lstrip("/")

            r = session.get(nextpageurl, timeout=30)
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
