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
        user_postcode = kwargs.get("postcode")
        user_paon = kwargs.get("paon")
        check_postcode(user_postcode)
        check_paon(user_paon)
        bindata = {"bins": []}

        # Get address ID from the streets endpoint
        streets_uri = "https://collectiondates.eastlothian.gov.uk/ajax/your-calendar/load-streets-summer-2025.asp"
        headers = {
            "Referer": "https://collectiondates.eastlothian.gov.uk/your-calendar",
            "User-Agent": "Mozilla/5.0",
        }
        
        response = requests.get(streets_uri, params={"postcode": user_postcode}, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        
        select = soup.find("select", id="SelectStreet")
        if not select:
            raise ValueError(f"No streets found for postcode {user_postcode}")
        
        address = select.find("option", string=lambda text: text and user_paon in text)
        if not address:
            raise ValueError(f"Address '{user_paon}' not found for postcode {user_postcode}")
        
        address_id = address["value"]
        
        # Get collection data using the correct endpoint
        collections_uri = "https://collectiondates.eastlothian.gov.uk/ajax/your-calendar/load-recycling-summer-2025.asp"
        response = requests.get(collections_uri, params={"id": address_id}, headers=headers)
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract collection details
        calendar_items = soup.find_all("div", class_="calendar-item")
        for item in calendar_items:
            waste_label = item.find("div", class_="waste-label").text.strip()
            waste_value = item.find("div", class_="waste-value").find("h4").text.strip()
            
            try:
                collection_date = datetime.strptime(
                    remove_ordinal_indicator_from_date_string(waste_value),
                    "%A %d %B %Y",
                )
                
                bindata["bins"].append({
                    "type": waste_label.replace(" is:", ""),
                    "collectionDate": collection_date.strftime(date_format),
                })
            except ValueError:
                continue
        
        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )
        
        return bindata
