from bs4 import BeautifulSoup
import requests, os

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import \
    AbstractGetBinDataClass


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:
        # Make a BS4 object

        data = {"bins": []}

        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/108.0.0.0 Safari/537.36"
        )
        headers = {"User-Agent": user_agent}

        address_street = "Valeside Gardens"

        # Stage 1 - Fetch initial page to get hidden form values needed for submission
        stage1_url = "https://apps.gedling.gov.uk/refuse/search.aspx"
        stage1_data = requests.get("https://apps.gedling.gov.uk/refuse/search.aspx", headers=headers)

        soup = BeautifulSoup(stage1_data.text, features="html.parser")
        try:
            value_viewstate = soup.find_all("input", {"id": "__VIEWSTATE"})[0]['value']
            value_viewstategenerator = soup.find_all("input", {"id": "__VIEWSTATEGENERATOR"})[0]['value']
            value_eventvalidation = soup.find_all("input", {"id": "__EVENTVALIDATION"})[0]['value']
        except:
            raise Exception("Beautiful Soup was not able to get the data back from the Stage 1 URL that we were expecting. Please raise an issue in GitHub")

        # Stage 2 - Now POST the query to get the bin data back
        stage2_url = "https://apps.gedling.gov.uk/refuse/search.aspx"
        post_data = {
            "__VIEWSTATE":value_viewstate,
            "__VIEWSTATEGENERATOR":value_viewstategenerator,
            "__EVENTVALIDATION":value_eventvalidation,
            "ctl00$MainContent$street":address_street,
            "ctl00$MainContent$mybutton":"Search"
        }

        stage2_request = requests.post(stage2_url,data=post_data,headers=headers)

        soup = BeautifulSoup(stage2_request.text, features="html.parser")

        bin_refuse_calendar = os.path.basename(soup.find_all('a', {"id": "ctl00_MainContent_streetgridview_ctl02_calendar1"})[0]['href'])
        bin_garden_calendar = os.path.basename(soup.find_all('a', {"id": "ctl00_MainContent_gardenGridView_ctl02_calendar2"})[0]['href'])

        bin_data = self.get_manual_data("refuse",bin_refuse_calendar)

        for k,v in bin_data.items():
            for date in v:

                dict_data = {
                    "type": k,
                    "collectionDate": date
                }

                data["bins"].append(dict_data)

        return data
    
    def get_manual_data(self,type,calendar):
        # Function to hold all the manual bin data extracted from the PDF's

        raw_data = {
            'refuse':{
                'FridayG1-2024.pdf':{
                    'Black Bin': ['08/12/2023', '22/12/2023', '05/01/2024', '19/01/2024', '02/02/2024', '16/02/2024', '01/03/2024', '15/03/2024', '29/03/2024', '12/04/2024', '26/04/2024', '10/05/2024', '24/05/2024', '07/06/2024', '21/06/2024', '05/07/2024', '19/07/2024', '02/08/2024', '16/08/2024', '30/08/2024', '13/09/2024', '27/09/2024', '11/10/2024', '25/10/2024', '08/11/2024', '22/11/2024'],
                    'Green Bin': ['01/12/2023', '15/12/2023', '29/12/2023', '12/01/2024', '26/01/2024', '09/02/2024', '23/02/2024', '08/03/2024', '22/03/2024', '05/04/2024', '19/04/2024', '03/05/2024', '17/05/2024', '31/05/2024', '14/06/2024', '28/06/2024', '12/07/2024', '26/07/2024', '09/08/2024', '23/08/2024', '06/09/2024', '20/09/2024', '04/10/2024', '18/10/2024', '01/11/2024', '15/11/2024', '29/11/2024'],
                    'Glass Box': ['01/12/2023', '29/12/2023', '26/01/2024', '23/02/2024', '22/03/2024', '19/04/2024', '17/05/2024', '14/06/2024', '12/07/2024', '09/08/2024', '06/09/2024', '04/10/2024', '01/11/2024', '29/11/2024']
                },
                'FridayG2-2024.pdf':{
                    'Black Bin': ['01/12/2023', '15/12/2023', '29/12/2023', '12/01/2024', '26/01/2024', '09/02/2024', '23/02/2024', '08/03/2024', '22/03/2024', '05/04/2024', '19/04/2024', '03/05/2024', '17/05/2024', '31/05/2024', '14/06/2024', '28/06/2024', '12/07/2024', '26/07/2024', '09/08/2024', '23/08/2024', '06/09/2024', '20/09/2024', '04/10/2024', '18/10/2024', '01/11/2024', '15/11/2024', '29/11/2024'],
                    'Green Bin': ['08/12/2023', '21/12/2023', '05/01/2024', '19/01/2024', '02/02/2024', '16/02/2024', '01/03/2024', '15/03/2024', '29/03/2024', '12/04/2024', '26/04/2024', '10/05/2024', '24/05/2024', '07/06/2024', '21/06/2024', '05/07/2024', '19/07/2024', '02/08/2024', '16/08/2024', '30/08/2024', '13/09/2024', '27/09/2024', '11/10/2024', '25/10/2024', '08/11/2024', '22/11/2024'],
                    'Glass Box': ['08/12/2023', '05/01/2024', '02/02/2024', '01/03/2024', '29/03/2024', '26/04/2024', '24/05/2024', '21/06/2024', '19/07/2024', '16/08/2024', '13/09/2024', '11/10/2024', '08/11/2024']
                },
                'FridayG3-2024.pdf':{
                    'Black Bin': ['08/12/2023', '21/12/2023', '05/01/2024', '19/01/2024', '02/02/2024', '16/02/2024', '01/03/2024', '15/03/2024', '29/03/2024', '12/04/2024', '26/04/2024', '10/05/2024', '24/05/2024', '07/06/2024', '21/06/2024', '05/07/2024', '19/07/2024', '02/08/2024', '16/08/2024', '30/08/2024', '13/09/2024', '27/09/2024', '11/10/2024', '25/10/2024', '08/11/2024', '22/11/2024'],
                    'Green Bin': ['01/12/2023', '15/12/2023', '29/12/2023', '12/01/2024', '26/01/2024', '09/02/2024', '23/02/2024', '08/03/2024', '22/03/2024', '05/04/2024', '19/04/2024', '03/05/2024', '17/05/2024', '31/05/2024', '14/06/2024', '28/06/2024', '12/07/2024', '26/07/2024', '09/08/2024', '23/08/2024', '06/09/2024', '20/09/2024', '04/10/2024', '18/10/2024', '01/11/2024', '15/11/2024', '29/11/2024'],
                    'Glass Box': ['15/12/2023', '12/01/2024', '09/02/2024', '08/03/2024', '05/04/2024', '03/05/2024', '31/05/2024', '28/06/2024', '26/07/2024', '23/08/2024', '20/09/2024', '18/10/2024', '15/11/2024']
                },
                'FridayG4-2024.pdf':{
                    'Black Bin': ['01/12/2023', '15/12/2023', '29/12/2023', '12/01/2024', '26/01/2024', '09/02/2024', '23/02/2024', '08/03/2024', '22/03/2024', '05/04/2024', '19/04/2024', '03/05/2024', '17/05/2024', '31/05/2024', '14/06/2024', '28/06/2024', '12/07/2024', '26/07/2024', '09/08/2024', '23/08/2024', '06/09/2024', '20/09/2024', '04/10/2024', '18/10/2024', '01/11/2024', '15/11/2024', '29/11/2024'],
                    'Green Bin': ['08/12/2023', '21/12/2023', '05/01/2024', '19/01/2024', '02/02/2024', '16/02/2024', '01/03/2024', '15/03/2024', '29/03/2024', '12/04/2024', '26/04/2024', '10/05/2024', '24/05/2024', '07/06/2024', '21/06/2024', '05/07/2024', '19/07/2024', '02/08/2024', '16/08/2024', '30/08/2024', '13/09/2024', '27/09/2024', '11/10/2024', '25/10/2024', '08/11/2024', '22/11/2024'],
                    'Glass Box': ['21/12/2023', '19/01/2024', '16/02/2024', '15/03/2024', '12/04/2024', '10/05/2024', '07/06/2024', '05/07/2024', '02/08/2024', '30/08/2024', '27/09/2024', '25/10/2024', '22/11/2024']
                }
            },
            'green': {

            }
        }
        
        return raw_data[type][calendar]
    

