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
    print(context.metadata['url'])
    args = [council, context.metadata['url']]
    parse_result = collect_data.main(args)
    print(parse_result)
    pass


@then("behave will test it for us!")
def step_impl(context):
    assert context.failed is False
