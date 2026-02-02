"""Constants for UK Bin Collection Data."""

from datetime import timedelta

from homeassistant.const import Platform

INPUT_JSON_URL = "https://raw.githubusercontent.com/robbrad/UKBinCollectionData/0.163.0/uk_bin_collection/tests/input.json"

DEFAULT_NAME = "UK Bin Collection Data"

DOMAIN = "uk_bin_collection"

LOG_PREFIX = "[UKBinCollection]"

PLATFORMS = [Platform.SENSOR]

STATE_ATTR_COLOUR = "colour"
STATE_ATTR_NEXT_COLLECTION = "next_collection"
STATE_ATTR_DAYS = "days"

DEVICE_CLASS = "bin_collection_schedule"

PLATFORMS = ["sensor", "calendar"]

SELENIUM_SERVER_URLS = ["http://localhost:4444", "http://selenium:4444"]

BROWSER_BINARIES = ["chromium", "chromium-browser", "google-chrome"]

EXCLUDED_ARG_KEYS = {
    "name",
    "council",
    "url",
    "skip_get_url",
    "local_browser",
    "timeout",
    "icon_color_mapping",
    "update_interval",
    "manual_refresh_only",
    "original_parser",
}
