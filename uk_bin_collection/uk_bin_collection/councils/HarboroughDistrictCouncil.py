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
        check_uprn(user_uprn)
        bindata = {"bins": []}

        URI = "https://harborough.fccenvironment.co.uk/detail-address"

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://harborough.fccenvironment.co.uk/",
        }
        params = {"Uprn": user_uprn}
        response = requests.post(URI, headers=headers, json=params, verify=False)

        # Check for service errors
        if response.status_code == 502:
            raise ValueError(
                f"The FCC Environment service is currently unavailable (502 Bad Gateway). "
                f"This is a temporary issue with the council's waste collection system. "
                f"Please try again later."
            )
        
        response.raise_for_status()

        soup = BeautifulSoup(response.content, features="html.parser")
        bin_collection = soup.find(
            "div", {"class": "blocks block-your-next-scheduled-bin-collection-days"}
        )
        
        if bin_collection is None:
            raise ValueError(
                f"Could not find bin collection data for UPRN {user_uprn}. "
                "The council website may have changed or the UPRN may be invalid."
            )
        
        lis = bin_collection.find_all("li")
        for li in lis:
            try:
                split = re.match(r"(.+)\s(\d{1,2} \w+ \d{4})$", li.text)
                bin_type = split.group(1).strip()
                date = split.group(2)

                dict_data = {
                    "type": bin_type,
                    "collectionDate": datetime.strptime(
                        date,
                        "%d %B %Y",
                    ).strftime("%d/%m/%Y"),
                }
                bindata["bins"].append(dict_data)
            except:
                continue

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
