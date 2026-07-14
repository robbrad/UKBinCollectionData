"""Constants for UK Bin Collection Data."""

from datetime import timedelta

from homeassistant.const import Platform

INPUT_JSON_URL = "https://raw.githubusercontent.com/robbrad/UKBinCollectionData/0.170.6/uk_bin_collection/tests/input.json"

DEFAULT_NAME = "UK Bin Collection Data"

DOMAIN = "uk_bin_collection"

LOG_PREFIX = "[UKBinCollection]"

PLATFORMS = [Platform.SENSOR, Platform.CALENDAR]

STATE_ATTR_COLOUR = "colour"
STATE_ATTR_NEXT_COLLECTION = "next_collection"
STATE_ATTR_DAYS = "days"

DEVICE_CLASS = "bin_collection_schedule"

SELENIUM_SERVER_URLS = ["http://localhost:4444", "http://selenium:4444"]

BROWSER_BINARIES = ["chromium", "chromium-browser", "google-chrome"]

CONFIG_ENTRY_VERSION = 4

SOUTH_KESTEVEN_COUNCIL = "SouthKestevenDistrictCouncil"
SOUTH_KESTEVEN_URL = "https://www.southkesteven.gov.uk/binday"

# Only these config-entry values are part of the core library's CLI contract.  In
# particular, unknown Home Assistant fields must never be forwarded to argparse.
STRING_ARGUMENTS = {
    "postcode": "--postcode",
    "number": "--number",
    "uprn": "--uprn",
    "usrn": "--usrn",
    "web_driver": "--web_driver",
    "artifact_dir": "--artifact-dir",
    "user_agent": "--user-agent",
}

TRUE_FLAG_ARGUMENTS = {
    "skip_get_url": "--skip_get_url",
    "local_browser": "--local_browser",
}
