import json
import requests
import sys
import base64
from tabulate import tabulate


def get_council_files(repo, branch):
    """
    Get a list of all .py council files in the 'councils' directory
    from the GitHub repo (via API), plus a mapping from council name
    to the file's GitHub 'download_url' or 'contents_url'.
    """
    url = f"https://api.github.com/repos/{repo}/contents/uk_bin_collection/uk_bin_collection/councils?ref={branch}"
    print(f"Fetching council files from: {url}")
    response = requests.get(url, headers={"Accept": "application/vnd.github.v3+json"})
    if response.status_code == 200:
        data = response.json()
        # data should be a list of items in that folder
        if isinstance(data, list):
            councils = {}
            for item in data:
                name = item["name"]
                if name.endswith(".py"):
                    council_name = name.replace(".py", "")
                    councils[council_name] = item["url"]  # 'url' gives API-based content URL
            return councils
        else:
            raise ValueError("Expected a list from the GitHub response but got something else.")
    else:
        print(f"Failed to fetch councils from files: {response.content}")
        return {}


def get_council_file_content(api_url):
    """
    Given the API URL for a file in GitHub, fetch its content (decoded).
    The 'download_url' is direct raw, but the 'url' is the API URL for the content.
    We'll use the latter, decode base64, and return the text.
    """
    # Example: https://api.github.com/repos/robbrad/UKBinCollectionData/contents/...
    response = requests.get(api_url, headers={"Accept": "application/vnd.github.v3+json"})
    if response.status_code == 200:
        file_json = response.json()
        # file_json["content"] is base64-encoded
        content = file_json.get("content", "")
        decoded = base64.b64decode(content).decode("utf-8")
        return decoded
    else:
        print(f"Failed to fetch file content: {response.content}")
        return ""


def get_input_json_data(repo, branch):
    """
    Fetch the entire input.json from GitHub and return it as a Python dict.
    """
    url = f"https://api.github.com/repos/{repo}/contents/uk_bin_collection/tests/input.json?ref={branch}"
    print(f"Fetching input JSON from: {url}")
    response = requests.get(url, headers={"Accept": "application/vnd.github.v3+json"})
    if response.status_code == 200:
        try:
            file_json = response.json()
            content = file_json.get("content", "")
            decoded = base64.b64decode(content).decode("utf-8")
            data = json.loads(decoded)
            return data
        except json.JSONDecodeError as e:
            print(f"JSON decoding error: {e}")
            raise
    else:
        print(f"Failed to fetch input JSON: {response.content}")
        return {}


def council_needs_update(council_name, json_data, council_file_content):
    """
    Check if the given council needs an update:
      - We say 'needs update' if 'web_driver' is missing in the JSON,
        BUT the script uses 'create_webdriver' in code.
    """
    # If the council isn't in the JSON at all, we can't do the check
    # (or we assume no JSON data => no web_driver?).
    council_data = json_data.get(council_name, {})
    web_driver_missing = ("web_driver" not in council_data)
    create_webdriver_present = ("create_webdriver" in council_file_content)

    return web_driver_missing and create_webdriver_present


def compare_councils(file_council_dict, json_data):
    """
    Compare councils in files vs councils in JSON, check for needs_update,
    and gather everything for final tabulation.

    Returns:
      - all_councils_data: dict keyed by council name:
            {
              "in_files": bool,
              "in_json": bool,
              "discrepancies_count": int,
              "needs_update": bool
            }
      - any_discrepancies_found: bool (if any differences in in_files vs in_json)
      - any_updates_needed: bool (if any council needs update)
    """
    file_councils = set(file_council_dict.keys())
    json_councils = set(json_data.keys())

    all_councils = file_councils.union(json_councils)
    all_council_data = {}

    any_discrepancies_found = False
    any_updates_needed = False

    for council in all_councils:
        in_files = council in file_councils
        in_json = council in json_councils
        # Count how many are False
        discrepancies_count = [in_files, in_json].count(False)

        # If the file is in the repo, fetch its content for checking
        content = ""
        if in_files:
            file_api_url = file_council_dict[council]
            content = get_council_file_content(file_api_url)

        # Evaluate "needs_update" only if the file is in place
        # (If there's no file, you might consider it "False" by default)
        needs_update = False
        if in_files:
            needs_update = council_needs_update(council, json_data, content)

        if discrepancies_count > 0:
            any_discrepancies_found = True
        if needs_update:
            any_updates_needed = True

        all_council_data[council] = {
            "in_files": in_files,
            "in_json": in_json,
            "discrepancies_count": discrepancies_count,
            "needs_update": needs_update,
        }

    return all_council_data, any_discrepancies_found, any_updates_needed


def main(repo="robbrad/UKBinCollectionData", branch="master"):
    print(f"Starting comparison for repo: {repo}, branch: {branch}")

    # 1) Get council file data (dict: { council_name: content_api_url, ... })
    file_council_dict = get_council_files(repo, branch)

    # 2) Get the entire JSON data
    json_data = get_input_json_data(repo, branch)

    # 3) Compare
    (
        all_councils_data,
        discrepancies_found,
        updates_needed,
    ) = compare_councils(file_council_dict, json_data)

    # 4) Print results
    table_data = []
    headers = ["Council Name", "In Files", "In JSON", "Needs Update?", "Discrepancies"]
    # Sort councils so that ones with the highest discrepancy or update appear first
    # Then alphabetical if tie:
    def sort_key(item):
        # item is (council_name, data_dict)
        return (
            item[1]["needs_update"],         # sort by needs_update (False < True)
            item[1]["discrepancies_count"],  # then by discrepancies
            item[0],                         # then by name
        )

    # We'll sort descending for "needs_update", so invert the boolean or reverse later
    sorted_councils = sorted(
        all_councils_data.items(),
        key=lambda x: (not x[1]["needs_update"], x[1]["discrepancies_count"], x[0])
    )

    for council, presence in sorted_councils:
        row = [
            council,
            "✔" if presence["in_files"] else "✘",
            "✔" if presence["in_json"] else "✘",
            "Yes" if presence["needs_update"] else "No",
            presence["discrepancies_count"],
        ]
        table_data.append(row)

    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    # 5) Determine exit code:
    #    If any discrepancies OR any council needs updates -> fail
    if discrepancies_found or updates_needed:
        print("Some discrepancies found or updates are needed. Failing workflow.")
        sys.exit(1)
    else:
        print("No discrepancies found and no updates needed. Workflow successful.")


if __name__ == "__main__":
    # Optional CLI args: python script.py <repo> <branch>
    repo_arg = sys.argv[1] if len(sys.argv) > 1 else "robbrad/UKBinCollectionData"
    branch_arg = sys.argv[2] if len(sys.argv) > 2 else "master"
    main(repo_arg, branch_arg)
