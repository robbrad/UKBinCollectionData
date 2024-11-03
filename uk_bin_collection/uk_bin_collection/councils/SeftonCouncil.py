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

        user_paon = kwargs.get("paon")
        user_postcode = kwargs.get("postcode")
        check_paon(user_paon)
        check_postcode(user_postcode)
        bindata = {"bins": []}

        sess = requests.Session()

        URI = "https://www.sefton.gov.uk/bins-and-recycling/bins-and-recycling/when-is-my-bin-collection-day/"

        request = sess.get(URI)

        soup = BeautifulSoup(request.content, "html.parser")
        hidden = soup.find_all("input", {"type": "hidden"}, limit=2)
        payload = {x["name"]: x["value"] for x in hidden}
        payload["Postcode"] = user_postcode
        payload["Streetname"] = user_paon
        request = sess.post(
            URI,
            data=payload,
        )
        # We should now have the page displaying the select list for addresses, parse again to find the form elements we need.
        soup = BeautifulSoup(request.content, "html.parser")
        hidden = soup.find_all("input", {"type": "hidden"})
        payload = {x["name"]: x["value"] for x in hidden}
        payload["action"] = "Select"
        option_tags = soup.select("select option")
        for option in option_tags:
            if option.text.upper().strip().startswith(user_paon):
                payload["selectedValue"] = option["value"]
                break
        request = sess.post(
            URI,
            data=payload,
        )
        soup = BeautifulSoup(request.content, "html.parser")
        tables = soup.find_all("table")
        if len(tables) > 0:
            for table in tables:
                binType = table.td.text.split()[0]
                binCollectionDate = table.td.findNext("td").findNext("td").text

                dict_data = {"type": binType, "collectionDate": binCollectionDate}
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
