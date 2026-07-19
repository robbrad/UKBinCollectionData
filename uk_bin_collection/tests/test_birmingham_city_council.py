"""Regression tests for Birmingham's standalone runtime dependency boundary."""

from __future__ import annotations

import builtins
import importlib
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


MODULE_NAME = (
    "uk_bin_collection.uk_bin_collection.councils.BirminghamCityCouncil"
)
COLLECTION_URL = (
    "https://www.birmingham.gov.uk/info/50388/check_your_collection_day"
)


def test_birmingham_import_does_not_require_yarl(monkeypatch) -> None:
    """The packaged council module must use only declared runtime dependencies."""
    sys.modules.pop(MODULE_NAME, None)
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "yarl" or name.startswith("yarl."):
            raise ModuleNotFoundError("No module named 'yarl'", name="yarl")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    module = importlib.import_module(MODULE_NAME)

    assert module.CouncilClass.__name__ == "CouncilClass"


def test_birmingham_passes_address_as_requests_query_parameters() -> None:
    module = importlib.import_module(MODULE_NAME)
    response = SimpleNamespace(
        text='<table class="data-table"><tbody></tbody></table>',
        raise_for_status=MagicMock(),
    )
    postcode = "B1 1AA"
    uprn = "100000000001"

    with (
        patch.object(module, "check_uprn"),
        patch.object(module, "check_postcode"),
        patch.object(module.requests, "get", return_value=response) as get,
    ):
        result = module.CouncilClass().parse_data(
            "",
            postcode=postcode,
            uprn=uprn,
        )

    assert result == {"bins": []}
    response.raise_for_status.assert_called_once_with()
    get.assert_called_once_with(
        COLLECTION_URL,
        params={"postcode": postcode, "uprn": uprn},
        headers=module.HEADERS,
        timeout=30,
    )
