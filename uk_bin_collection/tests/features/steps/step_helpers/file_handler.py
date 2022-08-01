import json
import os
from jsonschema import validate, ValidationError


def load_inputs_file(file_name):
    cwd = os.getcwd()
    with open(os.path.join(cwd, "uk_bin_collection", "tests", file_name)) as f:
        data = json.load(f)
    return data


def load_schema_file(file_name):
    cwd = os.getcwd()
    with open(
        os.path.join(cwd, "uk_bin_collection", "tests", "council_schemas", file_name)
    ) as f:
        data = json.load(f)
    return data


def validate_json(json_str):
    try:
        json.loads(json_str)
    except ValueError as err:
        return False
    return True


def validate_json_schema(json_str, schema):
    json_data = json.loads(json_str)
    try:
        validate(instance=json_data, schema=schema)
    except ValidationError as err:
        return False
    return True
