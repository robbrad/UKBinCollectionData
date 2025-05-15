import datetime

from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:

        try:
            user_uprn = kwargs.get("uprn")
            check_uprn(user_uprn)
            url = f"https://onlineservices.glasgow.gov.uk/forms/RefuseAndRecyclingWebApplication/CollectionsCalendar.aspx?UPRN={user_uprn}"
            if not user_uprn:
                # This is a fallback for if the user stored a URL in old system. Ensures backwards compatibility.
                url = kwargs.get("url")
        except Exception as e:
            raise ValueError(f"Error getting identifier: {str(e)}")

        # Make a BS4 object
        page = requests.get(url, verify=False)
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        # Declare an empty dict for data, and pair icon source URLs with their respective bin type
        data = {"bins": []}
        bin_types = {
            "../Images/Bins/blueBin.gif": "Mixed recycling",
            "../Images/Bins/greenBin.gif": "General waste",
            "../Images/Bins/greyBin.gif": "Food waste",
            "../Images/Bins/brownBin.gif": "Organic waste",
            "../Images/Bins/purpleBin.gif": "Glass",
            "../Images/Bins/ashBin.gif": "Ash bin",
        }

        fieldset = soup.find("fieldset")
        ps = fieldset.find_all("p")
        for p in ps:
            collection = p.text.strip().replace("Your next ", "").split(".")[0]
            bin_type = collection.split(" day is")[0]
            collection_date = remove_ordinal_indicator_from_date_string(
                collection
            ).split("day is ")[1]
            if collection_date == "Today":
                collection_date = datetime.today().strftime(date_format)
            elif collection_date == "Tomorrow":
                collection_date = (datetime.today() + timedelta(days=1)).strftime(
                    date_format
                )
                print(collection_date)
            else:
                collection_date = datetime.strptime(
                    collection_date,
                    "%A %d %B %Y",
                ).strftime(date_format)
            dict_data = {
                "type": bin_type,
                "collectionDate": collection_date,
            }
            data["bins"].append(dict_data)

        # Find the page body with all the calendars
        body = soup.find("div", {"id": "Application_ctl00"})
        calendars = body.find_all_next("table", {"title": "Calendar"})
        # For each calendar grid, get the month and all icons within it. We only take icons with alt text, as this
        # includes the bin type while excluding spacers
        for item in calendars:
            icons = item.find_all("img")
            # For each icon, get the day box, so we can parse the correct day number and make a datetime
            for icon in icons:
                cal_item = icon.find_parent().find_parent()
                bin_date = datetime.strptime(
                    cal_item["title"].replace("today is ", ""),
                    "%A, %d %B %Y",
                )

                # If the collection date is in the future, we want the date. Select the correct type, add the new
                # datetime, then add to the list
                if datetime.now() <= bin_date:
                    dict_data = {
                        "type": bin_types.get(icon["src"]),
                        "collectionDate": bin_date.strftime(date_format),
                    }
                    data["bins"].append(dict_data)

        return data
