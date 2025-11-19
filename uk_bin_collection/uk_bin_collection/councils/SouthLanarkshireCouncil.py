import time
from datetime import timedelta

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
        data = {"bins": []}
        collection_types = [
            "non recyclable waste",
            "food and garden",
            "paper and card",
            "glass, cans and plastics",
        ]

        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        week_details = soup.find("div", {"class": "bin-dir-snip"})
        week_dates = week_details.find("div", {"class": "clearfix"}).find("p")
        week_collections = week_details.find_all_next("h4")

        results = re.search(
            "([A-Za-z0-9 ]+) to ([A-Za-z0-9 ]+)", week_dates.get_text().strip()
        )
        if results:
            week_start = datetime.strptime(results.groups()[0], "%A %d %B %Y")
            week_end = datetime.strptime(results.groups()[1], "%A %d %B %Y")
            week_days = (
                week_start + timedelta(days=i)
                for i in range((week_end - week_start).days + 1)
            )

            week_collection_types = []
            for week_collection in week_collections:
                week_collection = (
                    week_collection.get_text().strip().lower().replace("-", " ")
                )
                for collection_type in collection_types:
                    if collection_type in week_collection:
                        week_collection_types.append(collection_type)

            collection_schedule = (
                soup.find("div", {"class": "serviceDetails"})
                .find("table")
                .find_all_next("tr")
            )
            for day in week_days:
                for row in collection_schedule:
                    schedule_type = row.find("th").get_text().strip()
                    results2 = re.search("([^(]+)", row.find("td").get_text().strip())
                    schedule_cadence = row.find("td").get_text().strip().split(" ")[1]
                    if results2:
                        schedule_day = results2[1].strip()
                        for collection_type in week_collection_types:
                            collectionDate = None
                            if collection_type in schedule_type.lower():
                                if (
                                    day.weekday()
                                    == time.strptime(schedule_day, "%A").tm_wday
                                ):
                                    collectionDate = day.strftime(date_format)
                            else:
                                if "Fortnightly" in schedule_cadence:
                                    if (
                                        day.weekday()
                                        == time.strptime(schedule_day, "%A").tm_wday
                                    ):
                                        day = day + timedelta(days=7)
                                        collectionDate = day.strftime(date_format)

                            if schedule_type and collectionDate:
                                dict_data = {
                                    "type": schedule_type,
                                    "collectionDate": collectionDate,
                                }
                                data["bins"].append(dict_data)

        return data
