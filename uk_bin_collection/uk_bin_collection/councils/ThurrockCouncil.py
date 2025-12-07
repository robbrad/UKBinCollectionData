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

        """
        Generate scheduled bin collection entries for a property based on the property's collection weekday and postcode round.
        
        Parameters:
        	page (str): HTML page content (unused; accepted for API compatibility).
        	paon (str, in kwargs): Collection weekday name (e.g., "Monday") used to compute the offset from generated base dates.
        	postcode (str, in kwargs): Round identifier, either "Round A" or "Round B", which selects the alternating start dates.
        
        Returns:
        	dict: A dictionary with key "bins" containing a list of collection entries. Each entry is a dict with:
        		- "type" (str): Bin type, e.g., "Green/Grey Bin", "Blue Bin", "Brown Bin", or "Food Bin".
        		- "collectionDate" (str): Collection date formatted as "DD/MM/YYYY".
        """
        collection_day = kwargs.get("paon")
        round = kwargs.get("postcode")

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

        round_week = ["Round A", "Round B"]

        offset_days = days_of_week.index(collection_day)
        round_collection = round_week.index(round)

        if round_collection == 0:
            bluebrownstartDate = datetime(2025, 11, 17)
            greengreystartDate = datetime(2025, 11, 24)
        else:
            greengreystartDate = datetime(2025, 11, 17)
            bluebrownstartDate = datetime(2025, 11, 24)

        greengrey_dates = get_dates_every_x_days(greengreystartDate, 14, 28)
        bluebrown_dates = get_dates_every_x_days(bluebrownstartDate, 14, 28)
        food_dates = get_dates_every_x_days(greengreystartDate, 7, 56)

        for greengrey_date in greengrey_dates:

            collection_date = (
                datetime.strptime(greengrey_date, "%d/%m/%Y")
                + timedelta(days=offset_days)
            ).strftime("%d/%m/%Y")

            dict_data = {
                "type": "Green/Grey Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        for bluebrown_date in bluebrown_dates:

            collection_date = (
                datetime.strptime(bluebrown_date, "%d/%m/%Y")
                + timedelta(days=offset_days)
            ).strftime("%d/%m/%Y")

            dict_data = {
                "type": "Blue Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)
            dict_data = {
                "type": "Brown Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        for food_date in food_dates:

            collection_date = (
                datetime.strptime(food_date, "%d/%m/%Y") + timedelta(days=offset_days)
            ).strftime("%d/%m/%Y")

            dict_data = {
                "type": "Food Bin",
                "collectionDate": collection_date,
            }
            bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata