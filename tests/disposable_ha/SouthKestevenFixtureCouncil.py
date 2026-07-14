"""Disposable loopback adapter around the production South Kesteven flow."""

from __future__ import annotations

import os
from pathlib import Path

from uk_bin_collection.uk_bin_collection.councils.SouthKestevenDistrictCouncil import (
    CouncilClass as ProductionCouncilClass,
)


class CouncilClass(ProductionCouncilClass):
    """Use the production flow against the pod's loopback-only fixture service."""

    BIN_DAY_URL = "http://127.0.0.1:8081/binday"
    CHECKER_SCHEME = "http"
    CHECKER_HOST = "127.0.0.1"

    def parse_data(self, page: str, **kwargs) -> dict:
        evidence_dir = os.environ.get("UKBCD_TEST_EVIDENCE_DIR")
        if evidence_dir:
            evidence_path = Path(evidence_dir) / "south_kesteven_scrape_calls"
            with evidence_path.open("a", encoding="utf-8") as handle:
                handle.write("1\n")
        return super().parse_data(page, **kwargs)
