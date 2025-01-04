from datetime import datetime

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
        # Check the UPRN is valid
        check_uprn(user_uprn)

        api_url = f"https://www.salford.gov.uk/bins-and-recycling/bin-collection-days/your-bin-collections/?UPRN={user_uprn}"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.salford.gov.uk/bins-and-recycling/bin-collection-days/",
        }

        # Make a request to the API
        requests.packages.urllib3.disable_warnings()
        response = requests.get(api_url, headers=headers)

        # Make a BS4 object
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        # Get the div element
        div_element = soup.find("div", {"class": "wastefurther"})

        # Get the bins
        bin_lists = div_element.find_all("ul")

        # Loop through each <ul> tag to extract the bin information
        for i, bin_list in enumerate(bin_lists):
            # Find the <p> tag containing the bin type string
            bin_type = bin_list.find_previous_sibling("p").find("strong").text.strip()

            # Loop through each <li> tag in the <ul> tag to extract the collection date
            for li in bin_list.find_all("li"):
                # Convert the collection time to a datetime object
                collection_date = datetime.strptime(li.text, "%A %d %B %Y")

                # Add the bin to the data dict
                data["bins"].append(
                    {
                        # remove the ":" from the end of the bin type
                        "type": bin_type[:-1],
                        "collectionDate": collection_date,
                    }
                )

        # Sort the bins by collection time
        data["bins"] = sorted(data["bins"], key=lambda x: x["collectionDate"])

        # Convert the datetime objects to strings in the desired format
        for bin in data["bins"]:
            bin["collectionDate"] = bin["collectionDate"].strftime(date_format)

        return data
