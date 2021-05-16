#!/usr/bin/env python3

#This script pulls (in one hit) the data from Warick District Council Bins Data
from bs4 import BeautifulSoup
from get_bin_data import AbstractGetBinDataClass

#import the wonderful Beautiful Soup and the URL grabber
class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the base
    class. They can also override some operations with a default implementation.
    """

    def parse_data(self, page) -> None:
        #Make a BS4 object
        soup = BeautifulSoup(page.text, features="html.parser")
        soup.prettify()

        data = {"bins":[]}

        for element in soup.find_all("strong"):
        
            binType = element.next_element
            binType = binType.lstrip()
            collectionDate = element.next_sibling.next_element.next_element

            dict_data = {
             "type": binType,
             "collectionDate": collectionDate,
            }
            data["bins"].append(dict_data)

        return data