import importlib
import os
import sys

from get_bin_data import AbstractGetBinDataClass

# We use this method to dynamically import the council processor
SRC_PATH = os.path.join("councils")
module_path = os.path.realpath(os.path.join(os.path.dirname(__file__), SRC_PATH))
sys.path.append(module_path)


def client_code(get_bin_data_class: AbstractGetBinDataClass, address_url) -> None:
    """
    The client code calls the template method to execute the algorithm. Client
    code does not have to know the concrete class of an object it works with,
    as long as it works with objects through the interface of their base class.
    """

    get_bin_data_class.template_method(address_url)


if __name__ == "__main__":
    council_module_str = "LeedsCityCouncil"       # sys.argv[1]
    address_url = "https://www.leeds.gov.uk/residents/bins-and-recycling/check-your-bin-day"      # sys.argv[2]
    council_module = importlib.import_module(council_module_str)

    client_code(council_module.CouncilClass(), address_url)
