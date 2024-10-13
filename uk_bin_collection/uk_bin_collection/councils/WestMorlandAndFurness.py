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

        URI = f"https://www.westmorlandandfurness.gov.uk/bins-recycling-and-street-cleaning/waste-collection-schedule/view/{user_uprn}"

        headers = {
            "user-agent": "Mozilla/5.0",
        }

        current_year = datetime.now().year
        current_month = datetime.now().month

        response = requests.get(URI)

        soup = BeautifulSoup(response.text, "html.parser")
        # Extract links to collection shedule pages and iterate through the pages
        schedule = soup.findAll("div", {"class": "waste-collection__month"})
        for month in schedule:
            collectionmonth = datetime.strptime(month.find("h3").text, "%B")
            collectionmonth = collectionmonth.month
            collectiondays = month.findAll("li", {"class": "waste-collection__day"})
            for collectionday in collectiondays:
                day = collectionday.find(
                    "span", {"class": "waste-collection__day--day"}
                ).text.strip()
                collectiondate = datetime.strptime(day, "%d")
                collectiondate = collectiondate.replace(month=collectionmonth)
                bintype = collectionday.find(
                    "span", {"class": "waste-collection__day--colour"}
                ).text

                if (current_month > 9) and (collectiondate.month < 4):
                    collectiondate = collectiondate.replace(year=(current_year + 1))
                else:
                    collectiondate = collectiondate.replace(year=current_year)

                dict_data = {
                    "type": bintype,
                    "collectionDate": collectiondate.strftime("%d/%m/%Y"),
                }
                bindata["bins"].append(dict_data)

        bindata["bins"].sort(
            key=lambda x: datetime.strptime(x.get("collectionDate"), "%d/%m/%Y")
        )

        return bindata
