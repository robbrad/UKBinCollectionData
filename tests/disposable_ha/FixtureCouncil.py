"""Disposable non-Selenium council used only inside the offline test image."""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

from uk_bin_collection.uk_bin_collection.common import date_format
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """Return one deterministic future collection without importing Selenium."""

    def parse_data(self, page: str, **kwargs) -> dict:
        del page, kwargs
        evidence_dir = os.environ.get("UKBCD_TEST_EVIDENCE_DIR")
        if evidence_dir:
            evidence_path = Path(evidence_dir) / "non_selenium_scrape_calls"
            with evidence_path.open("a", encoding="utf-8") as handle:
                handle.write("1\n")
        return {
            "bins": [
                {
                    "type": "Fixture Bin",
                    "collectionDate": (date.today() + timedelta(days=7)).strftime(
                        date_format
                    ),
                }
            ]
        }
