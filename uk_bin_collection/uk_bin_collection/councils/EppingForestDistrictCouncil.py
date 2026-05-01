import requests

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        postcode = kwargs.get("postcode", "")
        data = {"bins": []}

        # Use postcodes.io to get BNG eastings/northings for the postcode
        pc_clean = postcode.replace(" ", "")
        geo_resp = requests.get(f"https://api.postcodes.io/postcodes/{pc_clean}")
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        if geo_data.get("status") != 200 or not geo_data.get("result"):
            raise ValueError(f"Could not geocode postcode {postcode}")

        eastings = geo_data["result"]["eastings"]
        northings = geo_data["result"]["northings"]

        # Query the ArcGIS feature layer directly with a point geometry
        feature_url = (
            "https://services-eu1.arcgis.com/SDWAhoV6ICvQHz6h/arcgis/rest/services/"
            "Website_WasteCollectionRoutes/FeatureServer/0/query"
        )
        params = {
            "geometry": f'{{"x":{eastings},"y":{northings},"spatialReference":{{"wkid":27700}}}}',
            "geometryType": "esriGeometryPoint",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "WasteCollectionDates_ResidualDa,WasteCollectionDates_RecyclingD,WasteCollectionDates_FoodAndGar",
            "returnGeometry": "false",
            "f": "json",
        }
        resp = requests.get(feature_url, params=params)
        resp.raise_for_status()
        result = resp.json()

        features = result.get("features", [])
        if not features:
            raise ValueError(f"No waste collection zone found for postcode {postcode}")

        attrs = features[0]["attributes"]

        # Map field names to bin types
        bin_map = {
            "WasteCollectionDates_ResidualDa": "Black Bin",
            "WasteCollectionDates_RecyclingD": "Blue Box and Recycling Sack",
            "WasteCollectionDates_FoodAndGar": "Green-lidded Bin",
        }

        for field, bin_type in bin_map.items():
            date_str = attrs.get(field)
            if date_str:
                try:
                    parsed = datetime.strptime(date_str.strip(), "%d/%m/%Y")
                    data["bins"].append(
                        {
                            "type": bin_type,
                            "collectionDate": parsed.strftime(date_format),
                        }
                    )
                except ValueError:
                    continue

        data["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), date_format)
        )

        return data
