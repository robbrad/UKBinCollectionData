import os
import shutil
import argparse
from common import update_input_json

def create_council(council_name: str, url: str) -> None:
    base_dir = "uk_bin_collection/uk_bin_collection"
    template_file = os.path.join(base_dir, "councils/council_class_template/councilclasstemplate.py")
    council_dir = os.path.join(base_dir, "councils")
    test_file = os.path.join("uk_bin_collection", "tests", "features", "validate_council_outputs.feature")
    cwd = os.getcwd()
    input_file_path = os.path.join(cwd, "uk_bin_collection", "tests", "input.json")

    # Create council file from template
    new_council_file = os.path.join(council_dir, f"{council_name}.py")
    shutil.copy(template_file, new_council_file)
    
    # Update the new council class
    with open(new_council_file, 'r') as file:
        filedata = file.read()
    
    filedata = filedata.replace("CouncilClassTemplate", council_name)
    
    with open(new_council_file, 'w') as file:
        file.write(filedata)
    
    # Update the test feature file
    with open(test_file, 'a') as file:
        file.write(f"\n\n\t\t@{council_name}\n\t\tExamples: {council_name}\n\t\t| council |\n\t\t| {council_name} |")

    # Update the input JSON
    update_input_json(council_name, url, input_file_path)

def main():
    parser = argparse.ArgumentParser(description="Create a new council script from a template.")
    parser.add_argument('council_name', type=str, help='The name of the council to be created.')
    parser.add_argument('url', type=str, help='The URL associated with the council.')

    args = parser.parse_args()
    
    create_council(args.council_name, args.url)

if __name__ == "__main__":
    main()
