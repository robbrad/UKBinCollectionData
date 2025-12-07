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

        """
        Parse West Norfolk council bin collection information and return a structured list of upcoming collections.
        
        This method extracts bin types and collection dates for the supplied UPRN from the West Norfolk council collection page and returns them sorted chronologically.
        
        Parameters:
            uprn (str): Unique Property Reference Number provided via kwargs key "uprn". The value will be validated and left-padded with zeros to 12 characters before use.
        
        Returns:
            dict: A dictionary with a "bins" key mapping to a list of entries. Each entry is a dict with:
                - "type" (str): The bin type as reported by the council.
                - "collectionDate" (str): The collection date formatted as "dd/mm/YYYY".
        """
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        user_uprn = user_uprn.zfill(12)
        bindata = {"bins": []}

        URI = "https://www.west-norfolk.gov.uk/info/20174/bins_and_recycling_collection_dates"

        headers = {
            "Cookie": f"bcklwn_uprn={user_uprn}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }

        # Make the GET request
        response = requests.get(URI, headers=headers)

        soup = BeautifulSoup(response.content, features="html.parser")
        soup.prettify()

        # Find all bin_date_container divs
        bin_date_containers = soup.find_all("div", class_="bin_date_container")

        # Loop through each bin_date_container
        for container in bin_date_containers:
            # Extract the collection date
            date = (
                container.find("h3", class_="collectiondate").text.strip().rstrip(":")
            )

            # Extract the bin type from the alt attribute of the img tag
            bin_type = container.find("img")["alt"]

            dict_data = {
                "type": bin_type,
                "collectionDate": datetime.strptime(
                    date,
                    "%A %d %B %Y",
                ).strftime("%d/%m/%Y"),
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata