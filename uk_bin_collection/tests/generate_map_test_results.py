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


def categorize_error(message):
    """Categorize a test failure into a human-readable error category."""
    if "TimeoutException" in message:
        return "selenium_timeout"
    if "should be non-empty" in message or "[] should be non-empty" in message:
        return "empty_bins"
    if "ConnectionError" in message or "NameResolutionError" in message:
        return "connection_error"
    if "NoSuchElementException" in message:
        return "element_not_found"
    if "ElementClickInterceptedException" in message:
        return "click_intercepted"
    if "ValueError" in message:
        return "value_error"
    if "AttributeError" in message:
        return "attribute_error"
    return "other"


def parse_junit_xml(path, detailed=False):
    tree = ET.parse(path)
    root = tree.getroot()

    results = {}

    for testcase in root.iter("testcase"):
        testname = testcase.attrib.get("name", "")
        council = extract_council_name(testname)
        if not council:
            continue

        failure = testcase.find("failure")
        error = testcase.find("error")

        if failure is not None or error is not None:
            elem = failure if failure is not None else error
            message = elem.get("message", "")
            first_line = message.split("\n")[0].strip()

            if detailed:
                results[council] = {
                    "status": "fail",
                    "error_category": categorize_error(message),
                    "error_summary": first_line[:200],
                    "duration": testcase.get("time", ""),
                }
            else:
                results[council] = "fail"
        else:
            if detailed:
                results[council] = {
                    "status": "pass",
                    "duration": testcase.get("time", ""),
                }
            else:
                results[council] = "pass"

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_test_results.py <junit.xml path> [--detailed]")
        sys.exit(1)

    junit_path = sys.argv[1]
    detailed = "--detailed" in sys.argv

    results = parse_junit_xml(junit_path, detailed=detailed)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
