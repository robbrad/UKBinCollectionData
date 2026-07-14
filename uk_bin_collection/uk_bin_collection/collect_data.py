import argparse
import ast
import importlib
import logging
import os
import re
import sys
from functools import lru_cache
from importlib import util as import_util
from pathlib import Path

from uk_bin_collection.uk_bin_collection.get_bin_data import (
    setup_logging,
    LOGGING_CONFIG,
)
from uk_bin_collection.uk_bin_collection.exceptions import (
    InvalidCouncilModuleError,
    MissingDependencyError,
)
from uk_bin_collection.uk_bin_collection.dependency_validation import (
    validate_websocket_client,
)

_LOGGER = logging.getLogger(__name__)

_COUNCIL_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_COUNCILS_PACKAGE = "uk_bin_collection.uk_bin_collection.councils"
_COUNCILS_DIRECTORY = Path(__file__).resolve().parent / "councils"


def _normalised_path(path: os.PathLike[str] | str) -> str:
    """Return a real, case-normalised path for import-origin comparisons."""
    return os.path.normcase(os.path.realpath(os.fspath(path)))


def _council_file(module_name: str) -> Path:
    """Return the trusted source location for a registered council."""
    return _COUNCILS_DIRECTORY / f"{module_name}.py"


@lru_cache(maxsize=None)
def council_requires_selenium(module_name: str) -> bool:
    """Return whether a trusted council imports Selenium at any runtime scope.

    Older adapters use both eager and function-local imports. Inspecting the full
    trusted source before import lets the loader validate Selenium's
    collision-prone ``websocket`` dependency before either form can execute.
    """
    council_file = _council_file(module_name)
    try:
        syntax_tree = ast.parse(
            council_file.read_text(encoding="utf-8"), filename=str(council_file)
        )
    except (OSError, SyntaxError, UnicodeError) as exc:
        raise InvalidCouncilModuleError(
            f"Council module {module_name!r} cannot be inspected safely."
        ) from exc

    for node in ast.walk(syntax_tree):
        if isinstance(node, ast.Import) and any(
            imported.name == "selenium" or imported.name.startswith("selenium.")
            for imported in node.names
        ):
            return True
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and (node.module == "selenium" or node.module.startswith("selenium."))
        ):
            return True
    return False


@lru_cache(maxsize=1)
def registered_council_modules() -> frozenset[str]:
    """Return council module names shipped in the installed core package."""
    return frozenset(
        council_file.stem
        for council_file in _COUNCILS_DIRECTORY.iterdir()
        if council_file.is_file()
        and council_file.suffix == ".py"
        and _COUNCIL_NAME_PATTERN.fullmatch(council_file.stem)
    )


def import_council_module(module_name: str, src_path: str = "councils"):
    """Import an allowlisted council by its fully qualified package name."""
    if src_path != "councils":
        raise InvalidCouncilModuleError(
            "Custom council import paths are not supported."
        )
    if not isinstance(module_name, str) or not _COUNCIL_NAME_PATTERN.fullmatch(
        module_name
    ):
        raise InvalidCouncilModuleError(
            "Council names must be simple Python identifiers."
        )

    if module_name not in registered_council_modules():
        raise InvalidCouncilModuleError(
            f"Council module {module_name!r} is not present in the installed registry."
        )

    if council_requires_selenium(module_name):
        try:
            selenium_spec = import_util.find_spec("selenium")
        except (AttributeError, ImportError, ValueError) as exc:
            raise MissingDependencyError(
                "Python cannot safely resolve the optional 'selenium' dependency."
            ) from exc
        if selenium_spec is None:
            raise MissingDependencyError(
                "The optional dependency 'selenium' is required for this council."
            )
        validate_websocket_client()

    qualified_name = f"{_COUNCILS_PACKAGE}.{module_name}"
    expected_file = _normalised_path(_council_file(module_name))
    try:
        specification = import_util.find_spec(qualified_name)
    except (AttributeError, ImportError, ValueError) as exc:
        raise InvalidCouncilModuleError(
            f"Council module {module_name!r} cannot be resolved safely."
        ) from exc

    if (
        specification is None
        or specification.origin is None
        or _normalised_path(specification.origin) != expected_file
    ):
        raise InvalidCouncilModuleError(
            f"Council module {module_name!r} resolves outside the installed registry."
        )

    council_module = importlib.import_module(qualified_name)
    module_file = getattr(council_module, "__file__", None)
    if module_file is None or _normalised_path(module_file) != expected_file:
        raise InvalidCouncilModuleError(
            f"Council module {module_name!r} loaded from an unexpected location."
        )
    if not hasattr(council_module, "CouncilClass"):
        raise InvalidCouncilModuleError(
            f"Council module {module_name!r} does not expose CouncilClass."
        )
    return council_module


class UKBinCollectionApp:
    def __init__(self):
        self.setup_arg_parser()
        self.parsed_args = None

    def setup_arg_parser(self):
        """Setup the argument parser for the script."""
        self.parser = argparse.ArgumentParser(
            description="UK Bin Collection Data Parser"
        )
        self.parser.add_argument(
            "module", type=str, help="Name of council module to use"
        )
        self.parser.add_argument(
            "URL", type=str, help="URL to parse - should be wrapped in double quotes"
        )
        self.parser.add_argument(
            "-p",
            "--postcode",
            type=str,
            help="Postcode to parse - should include a space and be wrapped in double quotes",
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
        self.parser.add_argument(
            "-u", "--uprn", type=str, help="UPRN to parse", required=False
        )
        self.parser.add_argument(
            "-us", "--usrn", type=str, help="USRN to parse", required=False
        )
        self.parser.add_argument(
            "-w",
            "--web_driver",
            type=str,
            help="URL for remote Selenium web driver - should be wrapped in double quotes",
            required=False,
        )
        self.parser.add_argument(
            "--artifact-dir",
            "--artifact_dir",
            dest="artifact_dir",
            type=str,
            help="Directory for council-specific debug artifacts when a live scrape fails",
            required=False,
        )
        self.parser.add_argument(
            "--user-agent",
            "--user_agent",
            dest="user_agent",
            type=str,
            help="Optional HTTP/browser user agent for council requests",
            required=False,
        )
        self.parser.add_argument(
            "--headless",
            dest="headless",
            action="store_true",
            help="Should Selenium be headless. Defaults to true. Can be set to false to debug council",
        )
        self.parser.add_argument(
            "--not-headless",
            dest="headless",
            action="store_false",
            help="Should Selenium be headless. Defaults to true. Can be set to false to debug council",
        )
        self.parser.set_defaults(headless=True)
        self.parser.add_argument(
            "--local_browser",
            dest="local_browser",
            action="store_true",
            help="Should Selenium be run on a remote server or locally. Defaults to false.",
            required=False,
        )
        self.parser.add_argument(
            "-d",
            "--dev_mode",
            action="store_true",
            help="Enables development mode - creates/updates entries in the input.json file for the council on each run",
            required=False,
        )
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
            usrn=self.parsed_args.usrn,
            skip_get_url=self.parsed_args.skip_get_url,
            web_driver=self.parsed_args.web_driver,
            artifact_dir=self.parsed_args.artifact_dir,
            user_agent=self.parsed_args.user_agent,
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
