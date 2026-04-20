import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        """
        Fetches bin collection dates for a given UPRN from the Armagh Banbridge Craigavon council website and returns them as structured bin data.

        Parameters:
            page (str): Ignored by this implementation.
            kwargs:
                uprn (str): Unique Property Reference Number used to look up the address schedule; required.

        Returns:
            dict: Dictionary with a "bins" key mapping to a list of collections.
        """
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        # The council's WAF closes the connection on bare or minimal User-Agent
        # strings (manifests as requests.exceptions.ConnectionError with
        # RemoteDisconnected). A full modern browser UA passes cleanly.
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
        }

        def extract_bin_schedule(soup, heading_class):
            section_heading = soup.find("div", class_=heading_class)
            if not section_heading:
                return []
            content_col = section_heading.find_next("div", class_="col-sm-12 col-md-9")
            if not content_col:
                return []
            return [h4.get_text(strip=True) for h4 in content_col.find_all("h4")]

        url = f"https://www.armaghbanbridgecraigavon.gov.uk/resident/binday-result/?address={user_uprn}"

        session = requests.Session()
        session.headers.update(headers)
        response = session.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for collection in extract_bin_schedule(soup, "heading bg-black"):
            bindata["bins"].append({"collectionDate": collection, "type": "Domestic"})
        for collection in extract_bin_schedule(soup, "heading bg-green"):
            bindata["bins"].append({"collectionDate": collection, "type": "Recycling"})
        for collection in extract_bin_schedule(soup, "heading bg-brown"):
            bindata["bins"].append({"collectionDate": collection, "type": "Garden"})

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x["collectionDate"], "%d/%m/%Y")
        )

        return bindata
