import argparse
import importlib
import os
import sys
import logging
from uk_bin_collection.uk_bin_collection.get_bin_data import (
    setup_logging,
    LOGGING_CONFIG,
)

_LOGGER = logging.getLogger(__name__)


def import_council_module(module_name, src_path="councils"):
    """Dynamically import the council processor module."""
    module_path = os.path.realpath(os.path.join(os.path.dirname(__file__), src_path))
    if module_path not in sys.path:
        sys.path.append(module_path)
    return importlib.import_module(module_name)


class UKBinCollectionApp:
    def __init__(self):
        self.setup_arg_parser()
        self.parsed_args = None

    def setup_arg_parser(self):
        """Setup the argument parser for the script."""
        self.parser = argparse.ArgumentParser(description="UK Bin Collection Data Parser")
        self.parser.add_argument("module", type=str, help="Name of council module to use")
        self.parser.add_argument("URL", type=str, help="URL to parse - should be wrapped in double quotes")
        self.parser.add_argument("-p", "--postcode", type=str, help="Postcode to parse - should include a space and be wrapped in double quotes", required=False)
        self.parser.add_argument("-n", "--number", type=str, help="House number to parse", required=False)
        self.parser.add_argument("-s", "--skip_get_url", action="store_true", help="Skips the generic get_url - uses one in council class", required=False)
        self.parser.add_argument("-u", "--uprn", type=str, help="UPRN to parse", required=False)
        self.parser.add_argument("-w", "--web_driver", type=str, help="URL for remote Selenium web driver - should be wrapped in double quotes", required=False)
        self.parser.add_argument("--headless", dest="headless", action="store_true", help="Should Selenium be headless. Defaults to true. Can be set to false to debug council")
        self.parser.add_argument("--not-headless", dest="headless", action="store_false", help="Should Selenium be headless. Defaults to true. Can be set to false to debug council")
        self.parser.set_defaults(headless=True)
        self.parser.add_argument("--local_browser", dest="local_browser", action="store_true", help="Should Selenium be run on a remote server or locally. Defaults to false.", required=False)
        self.parser.add_argument("-d", "--dev_mode", action="store_true", help="Enables development mode - creates/updates entries in the input.json file for the council on each run", required=False)
        self.parsed_args = None

    def set_args(self, args):
        """Parse the arguments from the command line."""
        self.parsed_args = self.parser.parse_args(args)

    def run(self):
        """Run the application with the provided arguments."""
        council_module = import_council_module(self.parsed_args.module)
        return self.client_code(
            council_module.CouncilClass(),
            self.parsed_args.URL,
            postcode=self.parsed_args.postcode,
            paon=self.parsed_args.number,
            uprn=self.parsed_args.uprn,
            skip_get_url=self.parsed_args.skip_get_url,
            web_driver=self.parsed_args.web_driver,
            headless=self.parsed_args.headless,
            local_browser=self.parsed_args.local_browser,
            dev_mode=self.parsed_args.dev_mode,
            council_module_str=self.parsed_args.module,
        )

    def client_code(self, get_bin_data_class, address_url, **kwargs):
        """
        Call the template method to execute the algorithm. Client code does not need
        to know the concrete class of an object it works with, as long as it works with
        objects through the interface of their base class.
        """
        return get_bin_data_class.template_method(address_url, **kwargs)


def run():
    """Set up logging and run the application."""
    global _LOGGER
    _LOGGER = setup_logging(LOGGING_CONFIG, None)
    app = UKBinCollectionApp()
    app.set_args(sys.argv[1:])
    print(app.run())


if __name__ == "__main__":
    run()
