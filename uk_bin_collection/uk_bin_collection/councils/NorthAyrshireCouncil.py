import time

import requests

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

        URI = f"https://www.maps.north-ayrshire.gov.uk/arcgis/rest/services/AGOL/YourLocationLive/MapServer/8/query?f=json&outFields=*&returnDistinctValues=true&returnGeometry=false&spatialRel=esriSpatialRelIntersects&where=UPRN%20%3D%20%27{user_uprn}%27"

        # Make the GET request
        response = requests.get(URI)

        # Parse the JSON response
        result_json = response.json()

        # Extract bin collection dates
        blue_bin = result_json["features"][0]["attributes"].get("BLUE_DATE_TEXT")
        if blue_bin:
            dict_data = {"type": "Blue Bin", "collectionDate": blue_bin}
            bindata["bins"].append(dict_data)
        grey_bin = result_json["features"][0]["attributes"].get("GREY_DATE_TEXT")
        if grey_bin:
            dict_data = {"type": "Grey Bin", "collectionDate": grey_bin}
            bindata["bins"].append(dict_data)
        purple_bin = result_json["features"][0]["attributes"].get("PURPLE_DATE_TEXT")
        if purple_bin:
            dict_data = {"type": "Purple Bin", "collectionDate": purple_bin}
            bindata["bins"].append(dict_data)
        brown_bin = result_json["features"][0]["attributes"].get("BROWN_DATE_TEXT")
        if brown_bin:
            dict_data = {"type": "Brown Bin", "collectionDate": brown_bin}
            bindata["bins"].append(dict_data)

        return bindata
