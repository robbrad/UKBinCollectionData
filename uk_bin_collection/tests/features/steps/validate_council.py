from behave import *
from step_helpers import file_handler

from uk_bin_collection.uk_bin_collection import collect_data

@given('the council: "{council_name}"')
def step_impl(context, council_name):
    council_input_data = file_handler.load_inputs_file("input.json")
    context.metadata = council_input_data[council_name]
    pass

@when('we scrape the data from "{council}"')
def step_impl(context, council):
    context.council = council
    args = [council, context.metadata['url']]
    context.parse_result = collect_data.main(args)
    pass

@then("the result is valid json")
def step_impl(context):
    valid_json = file_handler.validate_json(context.parse_result)
    assert valid_json is True

@then("the output should validate against the schema")
def step_impl(context):
    council_schema = file_handler.load_schema_file(f'{context.council}.schema')
    file_handler.validate_json_schema(context.parse_result, council_schema)
    assert context.failed is False

