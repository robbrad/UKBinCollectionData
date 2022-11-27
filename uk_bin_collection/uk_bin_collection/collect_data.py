import importlib
import argparse
import os
import sys

if os.name == "nt":
    from get_bin_data import AbstractGetBinDataClass
else:
    from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

# We use this method to dynamically import the council processor
SRC_PATH = os.path.join("councils")
module_path = os.path.realpath(os.path.join(os.path.dirname(__file__), SRC_PATH))
sys.path.append(module_path)


def client_code(
    get_bin_data_class: AbstractGetBinDataClass, address_url, **kwargs
) -> None:
    """
    The client code calls the template method to execute the algorithm. Client
    code does not have to know the concrete class of an object it works with,
    as long as it works with objects through the interface of their base class.
    """

    return get_bin_data_class.template_method(address_url, **kwargs)


def get_council_module(council_module_str):
    return importlib.import_module(council_module_str)


def main(args):
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("module", type=str, help="Name of council module to use")
    parser.add_argument(
        "URL", type=str, help="URL to parse - should be wrapped in double quotes"
    )
    parser.add_argument(
        "-p",
        "--postcode",
        type=str,
        help="Postcode to parse - should include a space and be wrapped in "
        "double-quotes",
        required=False,
    )
    parser.add_argument(
        "-n", "--number", type=str, help="House number to parse", required=False
    )
    parser.add_argument("-u", "--uprn", type=str, help="UPRN to parse", required=False)
    parsed_args = parser.parse_args(args)

    council_module_str = parsed_args.module
    address_url = parsed_args.URL
    council_module = get_council_module(council_module_str)
    postcode = parsed_args.postcode
    paon = parsed_args.number
    uprn = parsed_args.uprn

    return client_code(
        council_module.CouncilClass(),
        address_url,
        postcode=postcode,
        paon=paon,
        uprn=uprn,
    )

    # parse arguments using optparse or argparse or what have you


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
