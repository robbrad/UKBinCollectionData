import time

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

        API_URL = "https://maps.norwich.gov.uk/arcgis/rest/services/MyNorwich/PropertyDetails/FeatureServer/2/query"

        params = {
            "f": "json",
            "where": f"UPRN='{user_uprn}' or UPRN='0{user_uprn}'",
            "returnGeometry": "true",
            "spatialRel": "esriSpatialRelIntersects",
            "geometryType": "esriGeometryPolygon",
            "inSR": "4326",
            "outFields": "*",
            "outSR": "4326",
            "resultRecordCount": "1000",
        }

        r = requests.get(API_URL, params=params)

        data = r.json()
        data = data["features"][0]["attributes"]["WasteCollectionHtml"]
        soup = BeautifulSoup(data, "html.parser")

        alternateCheck = soup.find("p")
        if alternateCheck.text.__contains__("alternate"):
            alternateCheck = True
        else:
            alternateCheck = False

        strong = soup.find_all("strong")
        collections = []

        if alternateCheck:
            bin_types = strong[2].text.strip().replace(".", "").split(" and ")
            for bin in bin_types:
                collections.append(
                    (
                        bin.capitalize(),
                        datetime.strptime(strong[1].text.strip(), date_format),
                    )
                )

        else:
            p_tag = soup.find_all("p")
            i = 1
            for p in p_tag:
                bin_types = (
                    p.text.split("Your ")[1].split(" is collected")[0].split(" and ")
                )
                for bin in bin_types:
                    collections.append(
                        (
                            bin.capitalize(),
                            datetime.strptime(strong[1].text.strip(), date_format),
                        )
                    )
                i += 2

        if len(strong) > 3:
            collections.append(
                ("Garden", datetime.strptime(strong[4].text.strip(), date_format))
            )

        ordered_data = sorted(collections, key=lambda x: x[1])
        for item in ordered_data:
            dict_data = {
                "type": item[0] + " bin",
                "collectionDate": item[1].strftime(date_format),
            }
            bindata["bins"].append(dict_data)

        return bindata
