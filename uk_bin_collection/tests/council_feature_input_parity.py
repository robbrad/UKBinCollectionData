import json
import re
import requests
import sys
from tabulate import tabulate

def get_councils_from_files(repo, branch):
    url = f"https://api.github.com/repos/{repo}/contents/uk_bin_collection/uk_bin_collection/councils?ref={branch}"
    print(f"Fetching councils from files at URL: {url}")
    response = requests.get(url)
    
    # Debugging lines to check the response content and type
    print(f"Response Status Code (Files): {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"Parsed JSON Data (Files): {data}")
            # Ensure 'data' is a list before proceeding
            if isinstance(data, list):
                return [item['name'].replace('.py', '') for item in data if item['name'].endswith('.py')]
            else:
                print("Expected a list from the JSON response but got something else.")
                raise ValueError("Expected a list from the JSON response but got something else.")
        except json.JSONDecodeError as e:
            print(f"JSON decoding error: {e}")
            raise
    else:
        print(f"Failed to fetch councils from files: {response.content}")
        return []

def get_councils_from_json(repo, branch):
    url = f"https://raw.githubusercontent.com/{repo}/{branch}/uk_bin_collection/tests/input.json"
    print(f"Fetching councils from JSON at URL: {url}")
    response = requests.get(url)
    
    # Debugging lines to check the response content and type
    print(f"Response Status Code (JSON): {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = json.loads(response.text)
            print(f"Parsed JSON Data: {data}")
            return list(data.keys())
        except json.JSONDecodeError as e:
            print(f"JSON decoding error: {e}")
            raise
    else:
        print(f"Failed to fetch councils from JSON: {response.content}")
        return []

def get_councils_from_features(repo, branch):
    url = f"https://raw.githubusercontent.com/{repo}/{branch}/uk_bin_collection/tests/features/validate_council_outputs.feature"
    print(f"Fetching councils from features at URL: {url}")
    response = requests.get(url)
    
    # Debugging lines to check the response content and type
    print(f"Response Status Code (Features): {response.status_code}")
    
    if response.status_code == 200:
        content = response.text
        print(f"Fetched Features Content: {content[:500]}...")  # Print only the first 500 characters for brevity
        return re.findall(r'Examples:\s+(\w+)', content)
    else:
        print(f"Failed to fetch councils from features: {response.content}")
        return []

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

def main(repo="robbrad/UKBinCollectionData", branch="master"):
    # Execute and print the comparison
    print(f"Starting comparison for repo: {repo}, branch: {branch}")
    file_councils = get_councils_from_files(repo, branch)
    json_councils = get_councils_from_json(repo, branch)
    feature_councils = get_councils_from_features(repo, branch)

    print(f"Councils from files: {file_councils}")
    print(f"Councils from JSON: {json_councils}")
    print(f"Councils from features: {feature_councils}")

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
    repo = sys.argv[1] if len(sys.argv) > 1 else "robbrad/UKBinCollectionData"
    branch = sys.argv[2] if len(sys.argv) > 2 else "master"
    main(repo, branch)
