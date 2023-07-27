import json
import logging
from abc import ABC, abstractmethod
import requests

# Logging configuration
logging.basicConfig(
    format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
    level=logging.INFO,
)

# Import the wonderful Beautiful Soup and the URL grabber


class AbstractGetBinDataClass(ABC):
    """An abstract class that can be imported to handle the data received from the provided council class."""

    def template_method(self, address_url: str, **kwargs) -> str:
        """The main template method that is constructed"""
        this_url = address_url
        this_postcode = kwargs.get("postcode", None)
        this_paon = kwargs.get("paon", None)
        this_uprn = kwargs.get("uprn", None)
        this_usrn = kwargs.get("usrn", None)
        skip_get_url = kwargs.get("skip_get_url", False)
        dev_mode = kwargs.get("dev_mode", False)
        council_module_str = kwargs.get("council_module_str", None)

        if not skip_get_url:
            page = self.get_data(address_url)
            bin_data_dict = self.parse_data(
                page, postcode=this_postcode, paon=this_paon, uprn=this_uprn, usrn=this_usrn, url=this_url
            )
            json_output = self.output_json(bin_data_dict)
        else:
            bin_data_dict = self.parse_data("", postcode=this_postcode, paon=this_paon, uprn=this_uprn, usrn=this_usrn)
            json_output = self.output_json(bin_data_dict)

        if dev_mode and bin_data_dict.get("bins"):
            self.write_output_json(council_module_str, json_output)

        return json_output

    @classmethod
    def get_data(cls, url) -> str:
        """This method makes the request to the council"""
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        headers = {"User-Agent": user_agent}
        requests.packages.urllib3.disable_warnings()

        try:
            full_page = requests.get(url, headers=headers, verify=False)
            return full_page
        except requests.exceptions.RequestException as err:
            logging.error(f"Oops: Something Else {err}")
            raise

    @abstractmethod
    def parse_data(self, page: str, **kwargs) -> dict:
        """Abstract method that takes a page as a string"""

    @classmethod
    def output_json(cls, bin_data_dict: dict) -> str:
        """Method to output the JSON as a pretty printed string"""
        return json.dumps(bin_data_dict, sort_keys=False, indent=4)

    def write_output_json(self, council_module_str, json_output):
        # Implement this method or remove the condition if not needed.
        pass
