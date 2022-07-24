import importlib
import argparse
import os
import sys

from get_bin_data import AbstractGetBinDataClass

# We use this method to dynamically import the council processor
SRC_PATH = os.path.join("councils")
module_path = os.path.realpath(os.path.join(os.path.dirname(__file__), SRC_PATH))
sys.path.append(module_path)

parser = argparse.ArgumentParser(description="")
parser.add_argument("module", type=str, help="Name of council module to use")
parser.add_argument("URL", type=str, help="URL to parse")
parser.add_argument("-p", "--postcode", type=str, help="Postcode to parse", required=False)
parser.add_argument("-n", "--number", type=str, help="House number to parse", required=False)
parser.add_argument("-u", "--UPRN", type=str, help="UPRN to parse", required=False)
args = parser.parse_args()


def client_code(get_bin_data_class: AbstractGetBinDataClass, address_url, **kwargs) -> None:
    """
    The client code calls the template method to execute the algorithm. Client
    code does not have to know the concrete class of an object it works with,
    as long as it works with objects through the interface of their base class.
    """

    get_bin_data_class.template_method(address_url, **kwargs)


if __name__ == "__main__":
    council_module_str = args.module
    address_url = args.URL
    council_module = importlib.import_module(council_module_str)
    postcode = args.postcode
    paon = args.number
    uprn = args.uprn

    client_code(council_module.CouncilClass(), address_url, postcode=postcode, paon=paon, uprn=uprn)
