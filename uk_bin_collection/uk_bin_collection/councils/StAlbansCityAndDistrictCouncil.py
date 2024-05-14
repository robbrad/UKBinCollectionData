from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass
from dateutil import parser


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        data = {"bins": []}

        headers = {
            "Content-Type": "application/json; charset=UTF-8",
        }

        req_data = {"uprn": user_uprn, "noticeBoard": "default"}

        url = "https://gis.stalbans.gov.uk/NoticeBoard9/VeoliaProxy.NoticeBoard.asmx/GetServicesByUprnAndNoticeBoard"

        response = requests.post(url, json=req_data, headers=headers)

        collections_response = response.json()

        collections = []

        for collection in collections_response["d"]:
            collection_data = collection["ServiceHeaders"][0]
            bin_type = collection_data["TaskType"]
            collection_date = collection_data["Next"]
            next_collection = parser.isoparser().isoparse(collection_date)
            collections.append((bin_type, next_collection))

        ordered_data = sorted(collections, key=lambda x: x[1])

        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }
            data["bins"].append(dict_data)

        return data
