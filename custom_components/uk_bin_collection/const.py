"""Constants for UK Bin Collection Data."""

from datetime import timedelta

from homeassistant.const import Platform

INPUT_JSON_URL = "https://raw.githubusercontent.com/robbrad/UKBinCollectionData/0.172.5/uk_bin_collection/tests/input.json"

DEFAULT_NAME = "UK Bin Collection Data"

DOMAIN = "uk_bin_collection"

# Current config-entry schema version. Bumped to 4 to migrate the legacy
# `manual_refresh_only` flag to the positive `auto_refresh_enabled` flag.
CONFIG_ENTRY_VERSION = 4

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
    "auto_refresh_enabled",
    "original_parser",
}

# These values can identify a household, disclose a private endpoint, or
# contain credentials.  Keep them out of Home Assistant logs, which are often
# collected for diagnostics and shared outside the local installation.
SENSITIVE_CONFIG_KEYS = frozenset(
    {
        "name",
        "url",
        "uprn",
        "postcode",
        "number",
        "usrn",
        "web_driver",
        "selenium_url",
        "icon_color_mapping",
        "password",
        "token",
    }
)


def redact_config_data(data: dict) -> dict:
    """Return a shallow copy suitable for diagnostic logging."""
    return {
        key: "<redacted>" if key in SENSITIVE_CONFIG_KEYS else value
        for key, value in data.items()
    }
