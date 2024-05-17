import logging
import traceback
from typing import Any, Generator, Callable

import pytest
from pytest_bdd import scenario, given, when, then, parsers
from functools import wraps

from step_helpers import file_handler
from uk_bin_collection.uk_bin_collection import collect_data

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

@scenario("../features/validate_council_outputs.feature", "Validate Council Output")
def test_scenario_outline() -> None:
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

@pytest.fixture
@handle_test_errors
def context() -> Generator[Any, None, None]:
    class Context:
        metadata: dict[str, Any]
        council: str
        parse_result: Any

    return Context()

@handle_test_errors
@given(parsers.parse("the council: {council_name}"))
def get_council_step(context: Any, council_name: str) -> None:
    council_input_data = file_handler.load_json_file("input.json")
    context.metadata = council_input_data[council_name]

@handle_test_errors
@when(parsers.parse("we scrape the data from {council}"))
def scrape_step(context: Any, council: str, headless_mode: str, local_browser: str, selenium_url: str) -> None:
    context.council = council

    args = [council, context.metadata["url"]]

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
    assert file_handler.validate_json_schema(context.parse_result, council_schema), "Schema validation failed"
