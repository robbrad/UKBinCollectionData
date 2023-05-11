"""Module that contains an abstract class that can be imported to
handle the data recieved from the provided council class.

Keyword arguments: None
"""
import requests
import json
from uk_bin_collection.uk_bin_collection.common import write_output_json
from abc import ABC, abstractmethod
import logging
from logging.config import dictConfig

LOGGING_CONFIG = dict(
    version=1,
    formatters={"f": {"format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"}},
    handlers={
        "h": {"class": "logging.StreamHandler", "formatter": "f", "level": logging.INFO}
    },
    root={"handlers": ["h"], "level": logging.INFO},
)


def setup_logging(logging_config, logger_name):
    try:
        logging.config.dictConfig(logging_config)
        logger = logging.getLogger(logger_name)
        return logger
    except Exception as exp:
        raise exp


LOGGER = setup_logging(LOGGING_CONFIG, None)

# import the wonderful Beautiful Soup and the URL grabber


class AbstractGetBinDataClass(ABC):
    """An abstract class that can be imported to handle the data recieved from the provided
    council class.

    Keyword arguments: None
    """

    def template_method(self, address_url: str, **kwargs) -> None:  # pragma: no cover
        """The main template method that is constructed

        Keyword arguments:
        address_url -- the url to get the data from
        """
        this_postcode = kwargs.get("postcode", None)
        this_paon = kwargs.get("paon", None)
        this_uprn = kwargs.get("uprn", None)
        skip_get_url = kwargs.get("skip_get_url", None)
        dev_mode = kwargs.get("dev_mode", False)
        council_module_str = kwargs.get("council_module_str", None)
        if (
            not skip_get_url or skip_get_url is False
        ):  # we will not use the generic way to get data - needs a get data in the council class itself
            page = self.get_data(address_url)
            bin_data_dict = self.parse_data(
                page, postcode=this_postcode, paon=this_paon, uprn=this_uprn
            )
            json_output = self.output_json(bin_data_dict)
        else:
            bin_data_dict = self.parse_data(
                "", postcode=this_postcode, paon=this_paon, uprn=this_uprn
            )
            json_output = self.output_json(bin_data_dict)

        # if dev mode create/update council's output JSON if bin_data_dict is not empty
        if dev_mode is not None and dev_mode is True and bin_data_dict["bins"]:
            write_output_json(council_module_str, json_output)

        return json_output

    @classmethod
    def get_data(cls, url) -> str:
        """This method makes the request to the council

        Keyword arguments:
        url -- the url to get the data from
        """
        # Set a user agent so we look like a browser ;-)
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/108.0.0.0 Safari/537.36"
        )
        headers = {"User-Agent": user_agent}
        requests.packages.urllib3.disable_warnings()

        # Make the Request - change the URL - find out your property number
        try:
            full_page = requests.get(url, headers, verify=False)
            return full_page
        except requests.exceptions.HTTPError as errh:
            LOGGER.error(f"Http Error: {errh}")
            raise
        except requests.exceptions.ConnectionError as errc:
            LOGGER.error(f"Error Connecting: {errc}")
            raise
        except requests.exceptions.Timeout as errt:
            LOGGER.error(f"Timeout Error: {errt}")
            raise
        except requests.exceptions.RequestException as err:
            LOGGER.error(f"Oops: Something Else {err}")
            raise

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
