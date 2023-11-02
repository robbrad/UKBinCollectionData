import argparse
import importlib
import os
import sys

# We use this method to dynamically import the council processor
SRC_PATH = os.path.join("councils")
module_path = os.path.realpath(os.path.join(os.path.dirname(__file__), SRC_PATH))
sys.path.append(module_path)


class UKBinCollectionApp:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="")
        self.parser.add_argument("module", type=str, help="Name of council module to use")
        self.parser.add_argument(
            "URL", type=str, help="URL to parse - should be wrapped in double quotes"
        )
        self.parser.add_argument(
            "-p",
            "--postcode",
            type=str,
            help="Postcode to parse - should include a space and be wrapped in "
                 "double-quotes",
            required=False,
        )
        self.parser.add_argument(
            "-n", "--number", type=str, help="House number to parse", required=False
        )
        self.parser.add_argument(
            "-s",
            "--skip_get_url",
            action="store_true",
            help="Skips the generic get_url - uses one in council class",
            required=False,
        )
        self.parser.add_argument("-u", "--uprn", type=str, help="UPRN to parse", required=False)
        self.parser.add_argument(
            "-w",
            "--web_driver",
            help="URL for remote Selenium web driver - should be wrapped in double quotes",
            required=False,
        )
        self.parser.add_argument(
            "-d",
            "--dev_mode",
            action="store_true",
            help="Enables development mode - creates/updates outputs .json file for the council on each run",
            required=False,
        )
        self.parsed_args = None

    def set_args(self, args):
        self.parsed_args = self.parser.parse_args(args)

    def get_council_module(self, council_module_str):
        return importlib.import_module(council_module_str)

    def client_code(self, get_bin_data_class, address_url, **kwargs) -> None:
        """
        The client code calls the template method to execute the algorithm. Client
        code does not have to know the concrete class of an object it works with,
        as long as it works with objects through the interface of their base class.
        """
        return get_bin_data_class.template_method(address_url, **kwargs)

    def run(self):
        council_module_str = self.parsed_args.module
        address_url = self.parsed_args.URL
        council_module = self.get_council_module(council_module_str)
        postcode = self.parsed_args.postcode
        paon = self.parsed_args.number
        uprn = self.parsed_args.uprn
        skip_get_url = self.parsed_args.skip_get_url
        web_driver = self.parsed_args.web_driver
        dev_mode = self.parsed_args.dev_mode

        return self.client_code(
            council_module.CouncilClass(),
            address_url,
            postcode=postcode,
            paon=paon,
            uprn=uprn,
            skip_get_url=skip_get_url,
            web_driver=web_driver,
            dev_mode=dev_mode,
            council_module_str=council_module_str,
        )


if __name__ == "__main__":
    import sys

    app = UKBinCollectionApp()
    app.set_args(sys.argv[1:])
    data = app.run()
    print(data)
