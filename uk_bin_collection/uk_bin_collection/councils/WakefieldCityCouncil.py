# This script pulls (in one hit) the data
# from Warick District Council Bins Data
from bs4 import BeautifulSoup
from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

import requests


# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the base
    class. They can also override some operations with a default
    implementation.
    """

    def parse_data(self, page: str, **kwargs) -> dict:

        # UPRN passed in as an argument
        user_uprn = kwargs.get("uprn")
        check_uprn(user_uprn)

        #cookies = {
        #    'visid_incap_2049675':    'xZCc/tFgSzaFmZD7XkN3koJGuGMAAAAAQUIPAAAAAAB7QGC8d+Jmlk0i3y06Zer6',
        #    'WSS_FullScreenMode':     'false',
        #    'incap_ses_1184_2049675': 'a2ZQQ9lCM3wa4+23mWpuEHnAuGMAAAAAfl4ebLXAvItl6dCfbMEWoQ==',
        #}
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

        params = {
            'uprn': user_uprn,
        }

        s = requests.Session() #gets cookies and keeps them

        wakefield_session = s.get("https://www.wakefield.gov.uk/", headers=headers)
        print(wakefield_session)
        # Make a GET for the data with correct params and cookies
        response = s.get('https://www.wakefield.gov.uk/site/Where-I-Live-Results', params=params,
                                headers=headers, verify=False)

        # Have BS4 process the page
        soup = BeautifulSoup(response.text, features="html.parser")
        soup.prettify()
        data = {"bins": []}

        # Start a tuple for collections with (TYPE:DATE). Add the first for the bin types since they're separate
        # elements on the page. All dates are parsed from text to datetime
        collections = [("Household waste",
                        datetime.strptime(soup.select("#ctl00_PlaceHolderMain_Waste_output > div:nth-child(4) > "
                                                      "div:nth-child(3) > div:nth-child(2)")[0].text, "%d/%m/%Y")),
                       ("Mixed recycling",
                        datetime.strptime(soup.select("#ctl00_PlaceHolderMain_Waste_output > div:nth-child(6) > "
                                                      "div:nth-child(3) > div:nth-child(2)")[0].text, "%d/%m/%Y"))]

        # Process the hidden future collection dates by adding them to the tuple
        household_future_table = soup.find("table", {"class": "mb10 wilWasteContent RESIDUAL (D)FutureData"}) \
            .find_all("td")
        for x in household_future_table:
            collections.append(("Household waste", datetime.strptime(x.text, "%d/%m/%Y")))
        recycling_future_table = soup.find("table", {"class": "mb10 wilWasteContent RECYCLING (D)FutureData"})\
            .find_all("td")
        for x in recycling_future_table:
            collections.append(("Mixed recycling", datetime.strptime(x.text, "%d/%m/%Y")))

        # Order the data by datetime, then add to and return it as a dictionary
        ordered_data = sorted(collections, key=lambda x: x[1])
        data = {"bins": []}
        for item in ordered_data:
            dict_data = {
                "type":           item[0],
                "collectionDate": item[1].strftime(date_format)
            }
            data["bins"].append(dict_data)

        return data
