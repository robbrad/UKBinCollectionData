"""Unit tests for the retired FyldeCouncil module.

Fylde Borough Council moved its bin lookup behind a registered account on the
Digital Waste Portal, so the scraper was retired on 2026-10-15 and its
input.json entry removed. The module itself is kept, because
collect_data.import_council_module imports it by the name in each Home
Assistant user's saved config. These tests pin that contract: the module still
imports and still exposes CouncilClass, and parse_data fails with a message
that tells the user an account is now required and where to go instead.
"""

import pytest

from uk_bin_collection.uk_bin_collection.councils import FyldeCouncil
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


def test_council_class_is_still_importable():
    """Deleting the module would give HA users an ImportError, not a message."""
    assert issubclass(FyldeCouncil.CouncilClass, AbstractGetBinDataClass)


def test_parse_data_explains_the_account_requirement():
    with pytest.raises(NotImplementedError, match="requires a registered account"):
        FyldeCouncil.CouncilClass().parse_data("", uprn="100010402452")


def test_parse_data_points_at_the_waste_portal():
    with pytest.raises(NotImplementedError) as excinfo:
        FyldeCouncil.CouncilClass().parse_data("")

    message = str(excinfo.value)
    assert "https://new.fylde.gov.uk/wasteportal/" in message
    assert "retired" in message


def test_parse_data_raises_without_touching_the_network():
    """No requests import, no session, no call out - it fails immediately."""
    assert not hasattr(FyldeCouncil, "requests")


def test_fylde_is_not_in_input_json():
    """The entry is removed so the live suite and HA config flow drop it."""
    import json
    import pathlib

    input_json = pathlib.Path(__file__).parent / "input.json"
    assert "FyldeCouncil" not in json.loads(input_json.read_text(encoding="utf-8"))
