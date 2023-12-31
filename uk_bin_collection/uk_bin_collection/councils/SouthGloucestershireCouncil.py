from datetime import timedelta

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def format_bin_data(key: str, date: datetime):
    formatted_date = date.strftime(date_format)

    if re.match(r"^R\d+$", key) is not None:
        # RX matches both general waste and recycling
        return [
            ("General Waste (Black Bin)", formatted_date),
            ("Recycling & Food Waste", formatted_date),
        ]
    elif re.match(r"^G\d+$", key) is not None:
        return [("Garden Waste (Green Bin)", formatted_date)]
    elif re.match(r"^C\d+$", key) is not None:
        return [("Recycling & Food Waste", formatted_date)]
    else:
        return None


class CouncilClass(AbstractGetBinDataClass):
    def parse_data(self, page: str, **kwargs) -> dict:
        uprn = kwargs.get("uprn")
        check_uprn(uprn)

        api_url = (
            f"https://webapps.southglos.gov.uk/Webservices/SGC.RefuseCollectionService/RefuseCollectionService"
            f".svc/getCollections/{uprn}"
        )

        headers = {"content-type": "application/json"}

        response = requests.get(api_url, headers=headers)

        json_response = json.loads(response.content)
        if not json_response:
            raise ValueError("No collection data found for provided UPRN.")

        collection_data = json_response[0]

        today = datetime.today()
        eight_weeks = datetime.today() + timedelta(days=8 * 7)
        data = {"bins": []}
        collection_tuple = []

        for key in collection_data:
            if key == "CalendarName":
                continue

            item = collection_data[key]

            if item == "":
                continue

            collection_date = datetime.strptime(item, date_format)
            if today.date() <= collection_date.date() <= eight_weeks.date():
                bin_data = format_bin_data(key, collection_date)
                if bin_data is not None:
                    for bin_date in bin_data:
                        collection_tuple.append(bin_date)

        ordered_data = sorted(collection_tuple, key=lambda x: x[1])

        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1],
            }
            data["bins"].append(dict_data)

        return data
