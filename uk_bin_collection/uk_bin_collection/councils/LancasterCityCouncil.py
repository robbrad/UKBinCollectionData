from datetime import datetime

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
        # data to return
        data = {"bins": []}

        # start session
        # note: this ignores the given url
        base_url = "https://lcc-wrp.whitespacews.com"
        session = requests.Session()
        response = session.get(base_url + "/#!")
        links = [
            a["href"]
            for a in BeautifulSoup(response.text, features="html.parser").select("a")
        ]
        portal_link = ""
        for l in links:
            if "seq=1" in l:
                portal_link = l

        # fill address form
        response = session.get(portal_link)
        form = BeautifulSoup(response.text, features="html.parser").find("form")
        form_url = dict(form.attrs).get("action")
        payload = {
            "address_name_number": kwargs.get("number"),
            "address_street": "",
            "address_postcode": kwargs.get("postcode"),
        }

        # get (first) found address
        response = session.post(form_url, data=payload)
        links = [
            a["href"]
            for a in BeautifulSoup(response.text, features="html.parser").select("a")
        ]
        addr_link = ""
        for l in links:
            if "seq=3" in l:
                addr_link = base_url + "/" + l

        # get json formatted bin data for addr
        response = session.get(addr_link)
        new_soup = BeautifulSoup(response.text, features="html.parser")
        services = new_soup.find("section", {"id": "scheduled-collections"})
        
        if services is None:
            raise Exception("Could not find scheduled collections section on the page")
            
        services_sub = services.find_all("li")
        if not services_sub:
            raise Exception("No collection services found")
            
        for i in range(0, len(services_sub), 3):
            if i + 2 < len(services_sub):
                date_text = services_sub[i + 1].text.strip() if services_sub[i + 1] else None
                if date_text:
                    try:
                        dt = datetime.strptime(date_text, "%d/%m/%Y").date()
                        bin_type_element = BeautifulSoup(services_sub[i + 2].text, features="lxml").find("p")
                        if bin_type_element and bin_type_element.text:
                            data["bins"].append(
                                {
                                    "type": bin_type_element.text.strip().removesuffix(" Collection Service"),
                                    "collectionDate": dt.strftime(date_format),
                                }
                            )
                    except (ValueError, AttributeError) as e:
                        # Skip invalid date or missing elements
                        continue

        return data
