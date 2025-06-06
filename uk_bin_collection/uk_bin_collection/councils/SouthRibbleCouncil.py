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
        user_postcode = kwargs.get("postcode")
        check_uprn(user_uprn)
        check_postcode(user_postcode)
        bindata = {"bins": []}

        session_uri = "https://forms.chorleysouthribble.gov.uk/xfp/form/70"
        URI = "https://forms.chorleysouthribble.gov.uk/xfp/form/70#qc576c657112a8277ba6f954ebc0490c946168363_0"

        session = requests.Session()
        token_response = session.get(session_uri)
        soup = BeautifulSoup(token_response.text, "html.parser")
        token = soup.find("input", {"name": "__token"}).attrs["value"]

        form_data = {
            "__token": token,
            "page": "196",
            "locale": "en_GB",
            "qc576c657112a8277ba6f954ebc0490c946168363_0_0": user_postcode,
            "qc576c657112a8277ba6f954ebc0490c946168363_1_0": user_uprn,
            "next": "Next",
        }

        collection_response = session.post(URI, data=form_data)

        #collection_soup = BeautifulSoup(collection_response.text, "html.parser")
        

        soup = BeautifulSoup(collection_response.text, "html.parser")
        #print(soup)

        rows = soup.find("table").find_all("tr")

        # Form a JSON wrapper
        data: Dict[str, List[Dict[str, str]]] = {"bins": []}

        # Loops the Rows
        for row in rows:
            cells = row.find_all("td")
            
            if cells:
                bin_type = cells[0].get_text(strip=True)
                collection_next = cells[1].get_text(strip=True)

                print(bin_type)
                print(len(collection_next))

                if len(collection_next) != 1:
                    collection_date_obj = parse(collection_next).date()
                    # since we only have the next collection day, if the parsed date is in the past,
                    # assume the day is instead next month
                    if collection_date_obj < datetime.now().date():
                        collection_date_obj += relativedelta(months=1)
                    # Make each Bin element in the JSON
                    dict_data = {
                        "type": bin_type,
                        "collectionDate": collection_date_obj.strftime(date_format),
                    }
                    # Add data to the main JSON Wrapper
                    data["bins"].append(dict_data)
                    continue      
        return data