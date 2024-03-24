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
        api_url = "https://www.hounslow.gov.uk/homepage/86/recycling_and_waste_collection_day_finder"
        user_uprn = kwargs.get("uprn")

        # Check the UPRN is valid
        check_uprn(user_uprn)

        # Create the form data
        form_data = {
            "UPRN": user_uprn,
        }

        # Make a request to the API
        requests.packages.urllib3.disable_warnings()
        response = requests.post(api_url, data=form_data)

        # Make a BS4 object
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        # Get the div element
        div_element = soup.find("div", {"class": "bin_day_main_wrapper"})

        # Get all bins with their corresponding dates using list comprehension
        # This creates a list of tuples, where each tuple contains the bin type and collection date
        bins_with_dates = [
            (
                bin.get_text().strip(),
                h4.get_text().replace("This ", "").replace("Next ", ""),
            )
            # This first for loop iterates over each h4 element
            for h4 in div_element.find_all("h4")
            # This nested for loop iterates over each li element within the corresponding ul element
            for bin in h4.find_next_sibling("ul").find_all("li")
        ]

        for bin_type, collection_date in bins_with_dates:
            if '-' in collection_date:
                date_part = collection_date.split(" - ")[1]
                data["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": datetime.strptime(date_part,"%d %b %Y").strftime(date_format)
                    }
                )
            elif len(collection_date.split(" ")) == 4:
                data["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": datetime.strptime(collection_date,"%A %d %b %Y").strftime(date_format)
                    }
                )
            else:
                data["bins"].append(
                    {
                        "type": bin_type,
                        "collectionDate": datetime.strptime(collection_date,"%d %b %Y").strftime(date_format)
                    }
                )

        return data
