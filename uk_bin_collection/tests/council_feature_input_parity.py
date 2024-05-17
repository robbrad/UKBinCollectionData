import json
import re
import requests
import sys
from tabulate import tabulate

def get_councils_from_files(branch):
    url = f"https://api.github.com/repos/robbrad/UKBinCollectionData/contents/uk_bin_collection/uk_bin_collection/councils?ref={branch}"
    response = requests.get(url)
    data = response.json()
    return [item['name'].replace('.py', '') for item in data if item['name'].endswith('.py')]

def get_councils_from_json(branch):
    url = f"https://raw.githubusercontent.com/robbrad/UKBinCollectionData/{branch}/uk_bin_collection/tests/input.json"
    response = requests.get(url)
    data = json.loads(response.text)
    return list(data.keys())

def get_councils_from_features(branch):
    url = f"https://raw.githubusercontent.com/robbrad/UKBinCollectionData/{branch}/uk_bin_collection/tests/features/validate_council_outputs.feature"
    response = requests.get(url)
    content = response.text
    return re.findall(r'Examples:\s+(\w+)', content)

def compare_councils(councils1, councils2, councils3):
    set1 = set(councils1)
    set2 = set(councils2)
    set3 = set(councils3)
    all_councils = set1 | set2 | set3
    all_council_data = {}
    discrepancies_found = False
    for council in all_councils:
        in_files = council in set1
        in_json = council in set2
        in_features = council in set3
        discrepancies_count = [in_files, in_json, in_features].count(False)
        all_council_data[council] = {
            'in_files': in_files,
            'in_json': in_json,
            'in_features': in_features,
            'discrepancies_count': discrepancies_count
        }
        if discrepancies_count > 0:
            discrepancies_found = True
    return all_council_data, discrepancies_found

def main(branch="master"):
    # Execute and print the comparison
    file_councils = get_councils_from_files(branch)
    json_councils = get_councils_from_json(branch)
    feature_councils = get_councils_from_features(branch)

    all_councils_data, discrepancies_found = compare_councils(file_councils, json_councils, feature_councils)

    # Create a list of lists for tabulate, sort by discrepancies count and then by name
    table_data = []
    headers = ["Council Name", "In Files", "In JSON", "In Features", "Discrepancies"]
    for council, presence in sorted(all_councils_data.items(), key=lambda x: (x[1]['discrepancies_count'], x[0])):
        row = [
            council,
            "✔" if presence['in_files'] else "✘",
            "✔" if presence['in_json'] else "✘",
            "✔" if presence['in_features'] else "✘",
            presence['discrepancies_count']
        ]
        table_data.append(row)

    # Print the table using tabulate
    print(tabulate(table_data, headers=headers, tablefmt='grid'))

    if discrepancies_found:
        print("Discrepancies found! Failing the workflow.")
        sys.exit(1)
    else:
        print("No discrepancies found. Workflow successful.")

if __name__ == "__main__":
    branch = sys.argv[1] if len(sys.argv) > 1 else "master"
    main(branch)
