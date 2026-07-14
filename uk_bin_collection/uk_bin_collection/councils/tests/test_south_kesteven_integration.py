"""Integration tests for the South Kesteven binday Selenium flow."""

import pytest

from uk_bin_collection.uk_bin_collection.councils.SouthKestevenDistrictCouncil import (
    CouncilClass,
)
from uk_bin_collection.uk_bin_collection.exceptions import (
    AddressMismatchError,
    BrowserUnavailableError,
)


class TestSouthKestevenIntegration:
    """Integration tests for South Kesteven District Council."""

    EXPECTED_BIN_TYPES = {"Grey Bin", "Food Bin", "Black Bin", "Purple Bin"}

    def setup_method(self):
        self.council = CouncilClass()

    @pytest.mark.integration
    def test_real_binday_lookup(
        self,
        test_postcode,
        test_paon,
        test_url,
        test_web_driver,
        test_headless,
        tmp_path,
    ):
        try:
            result = self.council.parse_data(
                "",
                url=test_url,
                postcode=test_postcode,
                paon=test_paon,
                web_driver=test_web_driver,
                headless=test_headless,
                artifact_dir=str(tmp_path),
            )
        except BrowserUnavailableError as exc:
            pytest.skip(f"Selenium unavailable for integration test: {exc}")

        assert "bins" in result
        assert isinstance(result["bins"], list)
        assert result["bins"]
        assert {
            bin_entry["type"] for bin_entry in result["bins"]
        } <= self.EXPECTED_BIN_TYPES

        for bin_entry in result["bins"]:
            assert "type" in bin_entry
            assert "collectionDate" in bin_entry
            date_parts = bin_entry["collectionDate"].split("/")
            assert len(date_parts) == 3
            assert len(date_parts[0]) == 2
            assert len(date_parts[1]) == 2
            assert len(date_parts[2]) == 4

    @pytest.mark.integration
    def test_unknown_property_is_reported(
        self, test_postcode, test_url, test_web_driver, test_headless, tmp_path
    ):
        try:
            with pytest.raises(
                AddressMismatchError,
                match="configured property was not found",
            ):
                self.council.parse_data(
                    "",
                    url=test_url,
                    postcode=test_postcode,
                    paon="NOT_A_REAL_PROPERTY",
                    web_driver=test_web_driver,
                    headless=test_headless,
                    artifact_dir=str(tmp_path),
                )
        except BrowserUnavailableError as exc:
            pytest.skip(f"Selenium unavailable for integration test: {exc}")
