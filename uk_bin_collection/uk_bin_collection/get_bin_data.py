"""Get Bin Data

Keyword arguments:
None
"""

import json
import logging, logging.config
from abc import ABC, abstractmethod
import os
import requests
import urllib3

from uk_bin_collection.uk_bin_collection.common import update_input_json

_LOGGER = logging.getLogger(__name__)

LOGGING_CONFIG = dict(
    version=1,
    formatters={"f": {"format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"}},
    handlers={
        "h": {"class": "logging.StreamHandler", "formatter": "f", "level": logging.INFO}
    },
    root={"handlers": ["h"], "level": logging.INFO},
)


def setup_logging(logging_config, logger_name):
    """Set up logging configuration.

    Keyword arguments:
    logging_config -- the logging configuration dictionary
    logger_name -- the name of the logger
    """
    try:
        logging.config.dictConfig(logging_config)
        logger = logging.getLogger(logger_name)
        return logger
    except Exception as exp:
        raise exp


class AbstractGetBinDataClass(ABC):
    """An abstract class that can be imported to handle the data received from the provided
    council class.

    Keyword arguments: None
    """

    def template_method(self, address_url: str, **kwargs) -> None:  # pragma: no cover
        """The main template method that is constructed

        Keyword arguments:
        address_url -- the url to get the data from
        """
        this_url = address_url
        this_local_browser = kwargs.get("local_browser", False)
        if not this_local_browser:
            kwargs["web_driver"] = kwargs.get("web_driver", None)

        bin_data_dict = self.get_and_parse_data(this_url, **kwargs)
        json_output = self.output_json(bin_data_dict)

        # if dev mode create/update council's entry in the input.json
        if kwargs.get("dev_mode"):
            self.update_dev_mode_data(
                council_module_str=kwargs.get("council_module_str"),
                this_url=this_url,
                **kwargs,
            )

        return json_output

    def get_and_parse_data(self, address_url, **kwargs):
        """Get and parse data from the URL

        Keyword arguments:
        address_url -- the URL to get the data from
        """
        if not kwargs.get("skip_get_url"):
            page = self.get_data(address_url)
            bin_data_dict = self.parse_data(page, url=address_url, **kwargs)
        else:
            bin_data_dict = self.parse_data("", url=address_url, **kwargs)

        return bin_data_dict

    def update_dev_mode_data(self, council_module_str, this_url, **kwargs):
        """Update input.json if in development mode

        Keyword arguments:
        council_module_str -- the council module string
        this_url -- the URL used
        """
        cwd = os.getcwd()
        input_file_path = os.path.join(cwd, "uk_bin_collection", "tests", "input.json")
        update_input_json(
            council_module_str,
            this_url,
            input_file_path,
            postcode=kwargs.get("postcode"),
            paon=kwargs.get("paon"),
            uprn=kwargs.get("uprn"),
            usrn=kwargs.get("usrn"),
            web_driver=kwargs.get("web_driver"),
            skip_get_url=kwargs.get("skip_get_url"),
        )

    @classmethod
    def get_data(cls, url) -> str:
        """This method makes the request to the council

        Keyword arguments:
        url -- the url to get the data from
        """
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/108.0.0.0 Safari/537.36"
        )
        headers = {"User-Agent": user_agent}
        urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)

        try:
            full_page = requests.get(url, headers=headers, verify=False, timeout=120)
            return full_page
        except requests.exceptions.RequestException as err:
            _LOGGER.error(f"Request Error: {err}")
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
        bin_data_dict -- a dict of parsed data
        """
        json_data = json.dumps(bin_data_dict, sort_keys=False, indent=4)
        return json_data
