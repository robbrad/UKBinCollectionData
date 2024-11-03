import json
import logging
import traceback
from functools import wraps
from typing import Any, Callable, Generator

import pytest
from pytest_bdd import given, parsers, scenario, then, when
from step_helpers import file_handler

from uk_bin_collection.uk_bin_collection import collect_data

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")


def get_council_list():
    json_file_path = "uk_bin_collection/tests/input.json"  # Specify the correct path to the JSON file
    with open(json_file_path, "r") as file:
        data = json.load(file)
    logging.info(f"Council List: {list(data.keys())}")
    return list(data.keys())


@pytest.fixture(params=get_council_list())
def council(request):
    print(f"Running test for council: {request.param}")
    return request.param


@scenario("../features/validate_council_outputs.feature", "Validate Council Output")
@pytest.mark.no_homeassistant  # Apply marker here
def test_scenario_outline(council) -> None:
    pass


def handle_test_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in test '{func.__name__}': {e}")
            logging.error(traceback.format_exc())
            raise e

    return wrapper


class Context:
    def __init__(self):
        self.metadata: dict[str, Any] = {}
        self.council: str = ""
        self.parse_result: Any = None


@pytest.fixture(scope="module")
def context():
    return Context()


@handle_test_errors
@given(parsers.parse("the council"))
def get_council_step(context, council) -> None:
    council_input_data = file_handler.load_json_file("input.json")
    context.metadata = council_input_data[council]
    context.council = council


@handle_test_errors
@when(parsers.parse("we scrape the data from the council"))
def scrape_step(
    context: Any, headless_mode: str, local_browser: str, selenium_url: str
) -> None:

    args = [context.council, context.metadata["url"]]

    if "uprn" in context.metadata:
        uprn = context.metadata["uprn"]
        args.append(f"-u={uprn}")
    if "postcode" in context.metadata:
        postcode = context.metadata["postcode"]
        args.append(f"-p={postcode}")
    if "house_number" in context.metadata:
        house_number = context.metadata["house_number"]
        args.append(f"-n={house_number}")
    if "usrn" in context.metadata:
        usrn = context.metadata["usrn"]
        args.append(f"-us={usrn}")
    if headless_mode == "True":
        args.append("--headless")
    else:
        args.append("--not-headless")

    if local_browser == "False":
        args.append(f"-w={selenium_url}")
    if "skip_get_url" in context.metadata:
        args.append("-s")

    CollectData = collect_data.UKBinCollectionApp()
    CollectData.set_args(args)
    context.parse_result = CollectData.run()


@handle_test_errors
@then("the result is valid json")
def validate_json_step(context: Any) -> None:
    assert file_handler.validate_json(context.parse_result), "Invalid JSON output"


@handle_test_errors
@then("the output should validate against the schema")
def validate_output_step(context: Any) -> None:
    council_schema = file_handler.load_json_file("output.schema")
    assert file_handler.validate_json_schema(
        context.parse_result, council_schema
    ), "Schema validation failed"
