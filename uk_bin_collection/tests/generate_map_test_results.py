import sys
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
import re


def extract_council_name(testname):
    """
    Extracts the council name from the test name.
    E.g. "test_scenario_outline[BarnetCouncil]" => "barnetcouncil"
    """
    match = re.search(r"\[(.*?)\]", testname)
    if match:
        return match.group(1).strip().lower()
    return None


def parse_junit_xml(path):
    tree = ET.parse(path)
    root = tree.getroot()

    results = defaultdict(lambda: "pass")

    for testcase in root.iter("testcase"):
        testname = testcase.attrib.get("name", "")
        council = extract_council_name(testname)
        if not council:
            continue

        if testcase.find("failure") is not None or testcase.find("error") is not None:
            results[council] = "fail"

    return results


def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_test_results.py <junit.xml path>")
        sys.exit(1)

    junit_path = sys.argv[1]
    results = parse_junit_xml(junit_path)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
