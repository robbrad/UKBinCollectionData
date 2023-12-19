import requests, re, urllib.parse

from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass

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

        user_address = "{} {}".format(user_number,user_postcode)
        user_address = urllib.parse.quote(user_address)
        
        # This first URL checks against a string represenging the users address and returns values used for a second lookup. 
        stage1_url = "https://wlnk.statmap.co.uk/map/Cluster.svc/findLocation?callback=getAddressesCallback1702938375023&script=%5CCluster%5CCluster.AuroraScript%24&address={}".format(user_address)

        address_data = requests.get(stage1_url).text

        # Strip data and parse the JSON
        address_data = json.loads(re.sub('getAddressesCallback[\d]+\(', '', address_data)[:-2])
        
        if address_data['TotalHits'] == 0:
            raise Exception("No address found for string {}. See Wiki".format(user_address))
        elif address_data['TotalHits'] != 1:
            # Multiple hits returned. Lets pick the first one. We could raise an exception here if this causes problems. 
            pass
        
        # Pull out the address data needed for the next step
        address_id = address_data['Locations'][0]['Id']
        address_x = address_data['Locations'][0]['X']
        address_y = address_data['Locations'][0]['Y']

        stage2_url = "https://wlnk.statmap.co.uk/map/Cluster.svc/getpage?script=\Cluster\Cluster.AuroraScript$&taskId=bins&format=js&updateOnly=true&query=x%3D{}%3By%3D{}%3Bid%3D{}".format(address_x,address_y,address_id)

        bin_query = requests.get(stage2_url).text

        # Test that what we got is good
        if "injectCss" not in bin_query:
            raise Exception("Error. Data has not been returned correctly. Please raise an issue on the GitHub page")

        # Return only the HTML contained within the Javascript function payload. 
        pattern = 'document\.getElementById\("DR1"\)\.innerHTML="(.+)";'

        bin_html = re.findall(pattern, bin_query)

        if len(bin_html) != 1:
            # This exception is raised if the regular expression above finds anything other than one expected match. 
            raise Exception("Incorrect number of matches found during phase 2 search. Please raise an issue on the Github page")

        # Some silly python foo required here to unescape the unicode contained. 
        bin_html = bin_html[0].encode().decode('unicode-escape')

        soup = BeautifulSoup(bin_html, 'html.parser')

        collection_rows = soup.find("li", {"class": "auroraListItem"}).find_all("li")

        for row in collection_rows:
            
            # Get bin type
            bin_type = row.find("span").text

            # Get bin date
            bin_date_text = row.text
            pattern = '\d+\/\d+'
            bin_dates = re.findall(pattern, bin_date_text)

            input_date_format = "%d/%m"

            for bin_date in bin_dates:
                
                # The date returned from the webpage only gives DD/MM. So we need to add a year, but we can't simply add this year otherwise we would get it wrong at the end of the year. So we will test to see if the returned date + this year is in the future. If not, add next years date. 
                bin_dt = datetime.strptime(bin_date, input_date_format)
                bin_dt = bin_dt.replace(year = datetime.now().year)         

                if bin_dt.date() == datetime.today().date():    # Check if date is today. This is OK
                    pass
                elif bin_dt.date() < datetime.today().date():   # Check if the date is in the past. If so, increment the year
                    bin_dt = bin_dt.replace(year = bin_dt.year + 1)
                elif bin_dt.date() > datetime.today().date():   # Check if date is in the future. This is OK
                    pass
                else:
                    raise Exception("Date issue has occured. This should never happen. Please raise a bug in GitHub")

                dict_data = {
                    "type": bin_type,
                    "collectionDate": bin_dt.strftime(date_format)
                }

                data["bins"].append(dict_data)

        return data
