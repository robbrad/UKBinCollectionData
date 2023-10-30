import requests
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        user_postcode = kwargs.get("postcode")
        check_uprn(user_uprn)
        check_postcode(user_postcode)

        # Create the form data
        form_data = {
            "postcode": user_postcode,
            "email-address": "",
            "uprn": user_uprn,
            "gdprTerms": "Yes",
            "privacynoticeid": "323",
            "find": "Show me my collection days",
        }

        # Make a request to the API
        requests.packages.urllib3.disable_warnings()
        s = requests.Session()
        s.get(
            "https://www.calderdale.gov.uk/environment/waste/household-collections/collectiondayfinder.jsp",
            headers={
                "Referer": "https://www.calderdale.gov.uk/environment/waste/household-collections/collectiondayfinder.jsp",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
            }
        )
        response = s.post(
            "https://www.calderdale.gov.uk/environment/waste/household-collections/collectiondayfinder.jsp",
            data=form_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": "https://www.calderdale.gov.uk/environment/waste/household-collections/collectiondayfinder.jsp",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
            }
        )

        # Make a BS4 object
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}

        # Get collections
        row_index = 0
        for row in soup.find("table", {"id": "collection"}).find_all("tr"):
            # Skip headers row
            if row_index < 1:
                row_index += 1
                continue
            else:
                # Get bin info
                bin_info = row.find_all("td")
                # Get the bin type
                bin_type = bin_info[0].find("strong").get_text(strip=True)
                # Get the collection date
                collection_date = ""
                for p in bin_info[2].find_all("p"):
                    if "your next collection" in p.get_text(strip=True):
                        collection_date = datetime.strptime(
                            " ".join(p.get_text(strip=True).replace("will be your next collection.", "").split()),
                            "%A %d %B %Y"
                        )

                if collection_date != "":
                    # Append the bin type and date to the data dict
                    dict_data = {
                        "type": bin_type,
                        "collectionDate": collection_date.strftime(date_format)
                    }
                    data["bins"].append(dict_data)

                row_index += 1

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
