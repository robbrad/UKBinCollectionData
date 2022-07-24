# This script pulls (in one hit) the data
# from Warick District Council Bins Data

from bs4 import BeautifulSoup
from get_bin_data import AbstractGetBinDataClass
from xml.etree import ElementTree
import requests

# import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):

    """
    Concrete classes have to implement all abstract operations of the
    baseclass. They can also override some
    operations with a default implementation.
    """
    def get_data(cls, uprn, **kwargs) -> str:
        """This method makes the request to the council

        Keyword arguments:
        url -- the url to get the data from
        """
        # Set a user agent so we look like a browser ;-)
        user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
        headers = {"User-Agent": user_agent, "Content-Type": "text/xml"}

        # Make the Request - change the URL - find out your property number
        # URL
        url = "https://collections-torridge.azurewebsites.net/WebService2.asmx"
        # Post data
        post_data='<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><getRoundCalendarForUPRN xmlns="http://tempuri2.org/"><council>TOR</council><UPRN>'+uprn+'</UPRN><PW>wax01653</PW></getRoundCalendarForUPRN></soap:Body></soap:Envelope>'
        full_page = requests.post(url, headers=headers, data=post_data)

        return full_page


    def parse_data(self, page: str) -> dict:
        # Remove the soap wrapper
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'a': 'http://tempuri2.org/',
        }
        dom = ElementTree.fromstring(page.text)
        page = dom.find(
            './soap:Body'
            '/a:getRoundCalendarForUPRNResponse'
            '/a:getRoundCalendarForUPRNResult',
            namespaces,
        )
        # Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        data = {"bins": []}
        
        b_el = soup.find('b',text='GardenBin')
        dict_data = {
            "type": "GardenBin",
            "collectionDate": b_el.next_sibling.split(": ")[1],
        }
        data["bins"].append(dict_data)

        b_el = soup.find('b',text='Refuse')
        dict_data = {
            "type": "Refuse",
            "collectionDate": b_el.next_sibling.split(": ")[1],
        }
        data["bins"].append(dict_data)

        b_el = soup.find('b',text='Recycling')
        dict_data = {
            "type": "Recycling",
            "collectionDate": b_el.next_sibling.split(": ")[1],
        }
        data["bins"].append(dict_data)

        return data
