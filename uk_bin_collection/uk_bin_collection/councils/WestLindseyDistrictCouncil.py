import urllib.parse

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        data = {"bins": []}

        user_postcode = kwargs.get("postcode")
        user_number = kwargs.get("paon")

        user_address = "{} {}".format(user_number, user_postcode)
        user_address = urllib.parse.quote(user_address)

        # This first URL checks against a string representing the users address and returns values used for a second lookup.
        stage1_url = "https://wlnk.statmap.co.uk/map/Cluster.svc/findLocation?callback=getAddressesCallback1702938375023&script=%5CCluster%5CCluster.AuroraScript%24&address={}".format(
            user_address
        )

        address_data = requests.get(stage1_url).text

        # Strip data and parse the JSON
        address_data = json.loads(
            re.sub(r"getAddressesCallback\d+\(", "", address_data)[:-2]
        )

        if address_data["TotalHits"] == 0:
            raise Exception(
                "No address found for string {}. See Wiki".format(user_address)
            )
        elif address_data["TotalHits"] != 1:
            # Multiple hits returned. Let's pick the first one. We could raise an exception here if this causes problems.
            pass

        # Pull out the address data needed for the next step
        address_id = address_data["Locations"][0]["Id"]
        address_x = address_data["Locations"][0]["X"]
        address_y = address_data["Locations"][0]["Y"]

        stage2_url = fr"https://wlnk.statmap.co.uk/map/Cluster.svc/getpage?script=\Cluster\Cluster.AuroraScript$&taskId=bins&format=js&updateOnly=true&query=x%3D{address_x}%3By%3D{address_y}%3Bid%3D{address_id}"

        bin_query = requests.get(stage2_url).text

        # Test that what we got is good
        if "injectCss" not in bin_query:
            raise Exception(
                "Error. Data has not been returned correctly. Please raise an issue on the GitHub page"
            )

        # Return only the HTML contained within the Javascript function payload.
        pattern = r'document\.getElementById\("DR1"\)\.innerHTML="(.+)";'

        bin_html = re.findall(pattern, bin_query)

        if len(bin_html) != 1:
            # This exception is raised if the regular expression above finds anything other than one expected match.
            raise Exception(
                "Incorrect number of matches found during phase 2 search. Please raise an issue on the Github page"
            )

        # Some silly python foo required here to unescape the unicode contained.
        bin_html = bin_html[0].encode().decode("unicode-escape")

        soup = BeautifulSoup(bin_html, "html.parser")

        collection_rows = soup.find("li", {"class": "auroraListItem"}).find_all("li")

        collections = []

        for row in collection_rows:
            # Get bin type
            bin_type = row.find("span").text

            # Get bin date
            bin_date_text = row.text
            pattern = r"\d+\/\d+"
            bin_dates = re.findall(pattern, bin_date_text)

            for bin_date in bin_dates:
                # Split the bin date into day and month and build a full date with the current year
                split_date = bin_date.split("/")
                if len(split_date[0]) < 1:
                    raise ValueError("Error parsing dates retrieved from website")
                full_date = datetime(
                    datetime.now().year, int(split_date[1]), int(split_date[0])
                )
                # If the current month is December and one of the next collections is in January, increment the year
                if datetime.now().month == 12 and int(split_date[1]) < 12:
                    full_date = datetime(year=datetime.now().year + 1, month=int(split_date[1]), day=int(split_date[0]))

                # Since data in unordered, add to a tuple
                collections.append((bin_type.title(), full_date))

        # Sort the tuple by date
        ordered_data = sorted(collections, key=lambda x: x[1])

        # Add everything into the dictionary
        for item in ordered_data:
            dict_data = {
                "type": item[0],
                "collectionDate": item[1].strftime(date_format),
            }

            data["bins"].append(dict_data)

        return data

