import json
from abc import ABC, abstractmethod

# import the wonderful Beautiful Soup and the URL grabber
import requests


class AbstractGetBinDataClass(ABC):
    def template_method(self, address_url: str) -> None:
        page = self.get_data(address_url)
        bin_data_dict = self.parse_data(page)
        self.output_json(bin_data_dict)

    def get_data(self, url) -> str:
        # Set a user agent so we look like a browser ;-)
        user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
        headers = {"User-Agent": user_agent}

        # Make the Request - change the URL - find out your property number
        full_page = requests.get(url, headers)

        return full_page

    @abstractmethod
    def parse_data(self, page: str) -> dict:
        pass

    def output_json(self, bin_data_dict: dict) -> str:
        # Form a JSON wrapper
        # Make the JSON
        json_data = json.dumps(bin_data_dict, sort_keys=True, indent=4)

        # Output the data
        print(json_data)
