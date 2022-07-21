"""Module that contains an abstract class that can be imported to
handle the data recieved from the provided council class.

Keyword arguments: None
"""
import json
from abc import ABC, abstractmethod

# import the wonderful Beautiful Soup and the URL grabber
import requests


class AbstractGetBinDataClass(ABC):
    """An abstract class that can be imported to handle the data recieved from the provided
    council class.

    Keyword arguments: None
    """
    def template_method(self, address_url: str, **kwargs) -> None:
        """The main template method that is constructed

        Keyword arguments:
        address_url -- the url to get the data from
        """
        this_postcode = kwargs.get("postcode", None)
        this_paon = kwargs.get("paon", None)
        page = self.get_data(address_url)
        bin_data_dict = self.parse_data(page, postcode=this_postcode, paon=this_paon)
        self.output_json(bin_data_dict)

    @classmethod
    def get_data(cls, url) -> str:
        """This method makes the request to the council

        Keyword arguments:
        url -- the url to get the data from
        """
        # Set a user agent so we look like a browser ;-)
        user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
        headers = {"User-Agent": user_agent}

        # Make the Request - change the URL - find out your property number
        full_page = requests.get(url, headers)

        return full_page

    @abstractmethod
    def parse_data(self, page: str, **kwargs) -> dict:
        """Abstract method that takes a page as a string

        Keyword arguments:
        page -- a string from the requested page
        """

    @classmethod
    def output_json(cls, bin_data_dict: dict) -> str:
        """Method to output the json as a pretty printed string

        Keyword arguments:
        bin_data_dict -- a dict parsed data
        """
        # Form a JSON wrapper
        # Make the JSON

        json_data = json.dumps(bin_data_dict, sort_keys=False, indent=4)

        # Output the data
        print(json_data)
        return json_data
