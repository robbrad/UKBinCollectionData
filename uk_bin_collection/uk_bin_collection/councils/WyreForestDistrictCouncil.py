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

        collection_day = kwargs.get("paon")
        bindata = {"bins": []}

        days_of_week = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        refusestartDate = datetime(2024, 11, 25)
        recyclingstartDate = datetime(2024, 11, 18)

        offset_days = days_of_week.index(collection_day)

        refuse_dates = get_dates_every_x_days(refusestartDate, 14, 28)
        recycling_dates = get_dates_every_x_days(recyclingstartDate, 14, 28)

        for refuseDate in refuse_dates:

            collection_date = (
                datetime.strptime(refuseDate, "%d/%m/%Y") + timedelta(days=offset_days)
            ).strftime("%d/%m/%Y")

            dict_data = {
                "type": "Black/Grey Rubbish Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        for recyclingDate in recycling_dates:

            collection_date = (
                datetime.strptime(recyclingDate, "%d/%m/%Y")
                + timedelta(days=offset_days)
            ).strftime("%d/%m/%Y")

            dict_data = {
                "type": "Green Recycling Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
