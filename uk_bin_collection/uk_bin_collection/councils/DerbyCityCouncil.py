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
        Parse Derby's bin day webpage for the given UPRN and return extracted bin collection entries.
        
        This function requests Derby's BinDays page for the provided `uprn`, parses the HTML for bin collection entries, and returns a dictionary containing a "bins" list where each item is a mapping with the bin type and its collection date formatted as `DD/MM/YYYY`.
        
        Parameters:
            page (str): Unused by this implementation (kept for interface compatibility).
            uprn (str, optional): Unique Property Reference Number passed via kwargs; used to build the Derby bin-days URL.
        
        Returns:
            dict: A dictionary with a single key "bins" whose value is a list of objects:
                - "type" (str): The bin type description (e.g., "General waste", "Recycling").
                - "collectionDate" (str): Collection date formatted as `DD/MM/YYYY`.
        """
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)
        bindata = {"bins": []}

        URI = f"https://secure.derby.gov.uk/binday/BinDays/{user_uprn}"

        # Make the GET request
        session = requests.Session()
        response = session.get(URI)

        soup = BeautifulSoup(response.content, "html.parser")

        # Find all divs with class "binresult" which contain the bin collection information
        bin_results = soup.find_all("div", class_="binresult")

        # Loop through each bin result to extract date and bin type
        for result in bin_results:
            # Find the collection date
            date_text = result.find("p").strong.get_text(strip=True)

            # Find the bin type by looking at the 'alt' attribute of the img tag
            bin_type = result.find("img")["alt"]

            if bin_type != "No bins":
                dict_data = {
                    "type": bin_type,
                    "collectionDate": datetime.strptime(
                        date_text,
                        "%A, %d %B %Y:",
                    ).strftime(date_format),
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata