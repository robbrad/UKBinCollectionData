import json
import logging
from jsonschema import validate, ValidationError
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

# Dynamically compute the base path relative to this file's location
current_file_path = Path(__file__).resolve()
BASE_PATH = current_file_path.parent.parent.parent.parent / "tests"


def load_json_file(file_name, encoding="utf-8"):
    file_path = BASE_PATH / file_name
    try:
        with open(file_path, "r", encoding=encoding) as f:
            data = json.load(f)
            logging.info(f"{file_name} file successfully loaded")
            return data
    except UnicodeDecodeError as e:
        logging.error(f"Failed to load {file_name} with encoding {encoding}: {e}")
        raise


def validate_json(json_str):
    try:
        return json.loads(json_str)
    except ValueError as err:
        logging.error(f"JSON validation error: {err}")
        raise


def validate_json_schema(json_str, schema):
    json_data = validate_json(json_str)
    try:
        validate(instance=json_data, schema=schema)
    except ValidationError as err:
        logging.error(f"Schema validation error: {err}")
        logging.info(f"Data: {json_str}")
        logging.info(f"Schema: {schema}")
        raise
    return True