import json
import os
from jsonschema import validate, ValidationError

import logging


def load_inputs_file(file_name):
    cwd = os.getcwd()
    with open(os.path.join(cwd, "uk_bin_collection", "tests", file_name)) as f:
        data = json.load(f)
        logging.info(f"{file_name} Input file loaded")
    return data


def load_schema_file(file_name):
    cwd = os.getcwd()
    with open(
        os.path.join(cwd, "uk_bin_collection", "tests", "council_schemas", file_name)
    ) as f:
        data = json.load(f)
        logging.info(f"{file_name} Schema file loaded")
    return data


def validate_json(json_str):
    try:
        json.loads(json_str)
    except ValueError as err:
        logging.info(f"The following error occured {err}")
        return False
    return True


def validate_json_schema(json_str, schema):
    json_data = json.loads(json_str)
    try:
        validate(instance=json_data, schema=schema)
    except ValidationError as err:
        logging.info(f"The following error occured {err}")
        logging.info(f"Data: {json_str}")
        logging.info(f"Schema: {schema}")
        return False
    return True
