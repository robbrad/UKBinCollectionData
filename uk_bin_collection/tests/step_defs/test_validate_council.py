import logging
import pytest
import traceback
from pytest_bdd import scenario, given, when, then, parsers
from hamcrest import assert_that, equal_to

from step_helpers import file_handler
from uk_bin_collection.uk_bin_collection import collect_data

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

@scenario("../features/validate_council_outputs.feature", "Validate Council Output")
def test_scenario_outline():
    pass


@pytest.fixture
def context():
    class Context(object):
        pass

    return Context()


@given(parsers.parse("the council: {council_name}"))
def get_council_step(context, council_name):
    try:
        council_input_data = file_handler.load_inputs_file("input.json")
        context.metadata = council_input_data[council_name]
    except Exception as err:
        logging.error(traceback.format_exc())
        logging.info(f"Validate Output: {err}")
        raise (err)


@when(parsers.parse("we scrape the data from {council}"))
def scrape_step(context, council):
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
    if "SKIP_GET_URL" in context.metadata:
        args.append(f"-s")

    try:
        CollectData = collect_data.UKBinCollectionApp()
        CollectData.set_args(args)
        context.parse_result = CollectData.run()
    except Exception as err:
        logging.error(traceback.format_exc())
        logging.info(f"Schema: {err}")
        raise (err)


@then("the result is valid json")
def validate_json_step(context):
    try:
        valid_json = file_handler.validate_json(context.parse_result)
        assert_that(valid_json, True)
    except Exception as err:
        logging.error(traceback.format_exc())
        logging.info(f"Validate Output: {err}")
        logging.info(f"JSON Output: {context.parse_result}")
        raise (err)


@then("the output should validate against the schema")
def validate_output_step(context):
    try:
        council_schema = file_handler.load_schema_file(f"output.schema")
        schema_result = file_handler.validate_json_schema(
            context.parse_result, council_schema
        )
        assert_that(schema_result, True)
    except Exception as err:
        logging.error(traceback.format_exc())
        logging.info(f"Validate Output: {err}")
        logging.info(f"JSON Output: {context.parse_result}")
        raise (err)
