"""Constants for UK Bin Collection Data."""
import logging

from homeassistant.const import Platform

DEFAULT_NAME = "UK Bin Collection Data"

DOMAIN = "uk_bin_collection"

_LOGGER = logging.getLogger(__name__)

LOG_PREFIX = "[UKBinCollection] "

PLATFORMS = [Platform.SENSOR]
