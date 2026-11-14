"""Councils that accept the UPRN either as `uprn` or inside a stored URL.

Older Home Assistant configs have no `uprn` field at all: the property is identified by a
URL with the UPRN in it. These scrapers support that, but 0.173.5 made `check_uprn`
raise on a missing UPRN, and they called it *before* the URL fallback, so every legacy
install failed at setup with "Invalid UPRN" (#2294: Cheshire East, Liverpool).
"""

import importlib
from unittest.mock import patch

import pytest

COUNCILS = [
    # (council, fragment the UPRN-built URL contains, uprn)
    ("CheshireEastCouncil", "GetBartecJobList?uprn=", "100012830647"),
    ("DartfordBoroughCouncil", "WS_CHECK_COLLECTIONS.eb?UPRN=", "100060861698"),
    ("EastbourneBoroughCouncil", "house.php?uprn=", "100060055444"),
    ("GlasgowCityCouncil", "CollectionsCalendar.aspx?UPRN=", "906700034497"),
    ("HerefordshireCouncil", "blpu_uprn=", "200002607456"),
    ("LewesDistrictCouncil", "house.php?uprn=", "100060055444"),
    ("LiverpoolCityCouncil", "BinDatesTable?UPRN=", "38164600"),
    ("NewhamCouncil", "Details/Index/", "100023015781"),
]
LEGACY_URL = "https://stored-by-an-old-config.example/bins?uprn=12345"


class _StoppedAtTheRequest(Exception):
    """Raised by the patched requests.get so no network call is made."""


def _requested_url(council, **kwargs):
    module = importlib.import_module(
        f"uk_bin_collection.uk_bin_collection.councils.{council}"
    )
    with patch.object(module.requests, "get", side_effect=_StoppedAtTheRequest) as get:
        with pytest.raises(_StoppedAtTheRequest):
            module.CouncilClass().parse_data("", **kwargs)
    return get.call_args.args[0]


@pytest.mark.parametrize("council, fragment, uprn", COUNCILS)
def test_a_legacy_config_with_only_a_url_still_reaches_that_url(
    council, fragment, uprn
):
    assert _requested_url(council, url=LEGACY_URL) == LEGACY_URL
    assert _requested_url(council, url=LEGACY_URL, uprn=None) == LEGACY_URL
    assert _requested_url(council, url=LEGACY_URL, uprn="") == LEGACY_URL


@pytest.mark.parametrize("council, fragment, uprn", COUNCILS)
def test_a_uprn_wins_over_the_stored_url(council, fragment, uprn):
    requested = _requested_url(council, url=LEGACY_URL, uprn=uprn)
    assert requested != LEGACY_URL
    assert fragment in requested and uprn in requested


@pytest.mark.parametrize("council, fragment, uprn", COUNCILS)
def test_neither_a_uprn_nor_a_url_is_a_clear_error(council, fragment, uprn):
    module = importlib.import_module(
        f"uk_bin_collection.uk_bin_collection.councils.{council}"
    )
    with patch.object(module.requests, "get", side_effect=_StoppedAtTheRequest) as get:
        with pytest.raises(ValueError, match="Invalid UPRN"):
            module.CouncilClass().parse_data("")
    get.assert_not_called()
