"""Constants for UK Bin Collection Data."""
import logging
from datetime import timedelta

from homeassistant.const import Platform

DEFAULT_NAME = "UK Bin Collection Data"

DOMAIN = "uk_bin_collection"

_LOGGER = logging.getLogger(__name__)

LOG_PREFIX = "[UKBinCollection] "

PLATFORMS = [Platform.SENSOR]

SCAN_INTERVAL = timedelta(hours=24)
