import json
import os


def load_inputs_file(file_name):
    cwd = os.getcwd()
    with open(os.path.join(cwd, "uk_bin_collection", "tests", file_name)) as f:
        data = json.load(f)
    return data
