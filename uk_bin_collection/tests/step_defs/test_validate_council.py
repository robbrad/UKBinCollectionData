#from behave import *
import pytest
from pytest_bdd import scenario, given, when, then, parsers

from step_helpers import file_handler
import logging
import traceback

from uk_bin_collection.uk_bin_collection import collect_data

@scenario('../features/validate_council_outputs.feature', "Validate Council Output")
def test_scenario_outline():
    pass


@pytest.fixture
def context():
    class Context(object):
        pass

    return Context()

@given(parsers.parse('the council: {council_name}'))
def get_council_step(context, council_name):
    council_input_data = file_handler.load_inputs_file("input.json")
    context.metadata = council_input_data[council_name]
    pass

@when(parsers.parse('we scrape the data from {council}'))
def scrape_step(context, council):
    context.council = council
    args = [
        council,
        context.metadata["url"]
    ]
    
    if "uprn" in context.metadata:
        uprn = context.metadata["uprn"]
        args.append(f"-u={uprn}")
    if "postcode" in context.metadata:
        postcode = context.metadata["postcode"]
        args.append(f"-p={postcode}")
    if "house_number" in context.metadata:
        house_number = context.metadata["house_number"]
        args.append(f"-n={house_number}")
    if "SKIP_GET_URL" in context.metadata:
        skip_url = context.metadata["SKIP_GET_URL"]
        args.append(f"-s={skip_url}")
    
    try:
        context.parse_result = collect_data.main(args)
    except Exception as err:
        logging.error(traceback.format_exc())
        logging.info(f"Schema: {err}")
    pass


@then("the result is valid json")
def validate_json_step(context):
    valid_json = file_handler.validate_json(context.parse_result)
    assert valid_json is True


@then("the output should validate against the schema")
def validate_output_step(context):
    council_schema = file_handler.load_schema_file(f"{context.council}.schema")
    schema_result = file_handler.validate_json_schema(
        context.parse_result, council_schema
    )
    assert schema_result is True
