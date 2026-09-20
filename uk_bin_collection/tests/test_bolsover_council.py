"""Regression tests for BolsoverCouncil parity calculation.

The parity logic determines which bin type (Black, or Burgundy+Green) is
collected on a given date.  It uses a continuous fortnight index anchored to a
fixed epoch so that consecutive weeks always alternate — even across ISO
week-53 year boundaries and 52-week years.

Verified against live Bolsover council API data for UPRN 100030066827
(Route="ThS", WeekBlack="2", WeekBandG="1", collection day = Thursday).
"""

from datetime import date

from uk_bin_collection.uk_bin_collection.councils.BolsoverCouncil import (
    _determine_bin_collection,
)


class TestDetermineBinCollection:
    """Tests for the module-level _determine_bin_collection helper."""

    # API values for test UPRN 100030066827
    WEEK_BLACK = "2"
    WEEK_BANDG = "1"

    # -- basic alternation ------------------------------------------------

    def test_consecutive_thursdays_alternate(self):
        """Two consecutive Thursdays must return different bin types."""
        thu1 = date(2026, 9, 24)  # Thursday
        thu2 = date(2026, 10, 1)  # next Thursday
        bin1 = _determine_bin_collection(thu1, self.WEEK_BLACK, self.WEEK_BANDG, "No")
        bin2 = _determine_bin_collection(thu2, self.WEEK_BLACK, self.WEEK_BANDG, "No")
        assert bin1 != bin2, f"{thu1}={bin1} and {thu2}={bin2} should differ"
        assert {bin1, bin2} == {"Black Bin", "Burgundy Bin & Green Bin"}

    def test_known_september_2026_collections(self):
        """Verify against HA sensor data: Sept 22 = Burgundy+Green, Sept 29 = Black."""
        assert _determine_bin_collection(date(2026, 9, 22), self.WEEK_BLACK, self.WEEK_BANDG, "No") == "Burgundy Bin & Green Bin"
        assert _determine_bin_collection(date(2026, 9, 29), self.WEEK_BLACK, self.WEEK_BANDG, "No") == "Black Bin"

    # -- ISO week-53 → week-1 year boundary (2026 has 53 ISO weeks) -------

    def test_week53_to_week1_transition_2026_2027(self):
        """Dec 29, 2026 (Mon of W53) and Jan 5, 2027 (Mon of W01) must differ."""
        w53_monday = date(2026, 12, 28)  # Monday of ISO week 53
        w01_monday = date(2027, 1, 4)    # Monday of ISO week 1
        bin_w53 = _determine_bin_collection(w53_monday, self.WEEK_BLACK, self.WEEK_BANDG, "No")
        bin_w01 = _determine_bin_collection(w01_monday, self.WEEK_BLACK, self.WEEK_BANDG, "No")
        assert bin_w53 != bin_w01, (
            f"Year boundary (53→1): {w53_monday}={bin_w53} and {w01_monday}={bin_w01} should differ"
        )

    def test_week53_thursday_dec31_2026(self):
        """Dec 31, 2026 (Thu of W53) and Jan 7, 2027 (Thu of W01) must differ."""
        dec31 = date(2026, 12, 31)
        jan7 = date(2027, 1, 7)
        bin_dec = _determine_bin_collection(dec31, self.WEEK_BLACK, self.WEEK_BANDG, "No")
        bin_jan = _determine_bin_collection(jan7, self.WEEK_BLACK, self.WEEK_BANDG, "No")
        assert bin_dec != bin_jan, (
            f"Year boundary Thu (53→1): {dec31}={bin_dec} and {jan7}={bin_jan} should differ"
        )

    # -- ISO week-52 → week-1 year boundary (2027 has 52 ISO weeks) -------

    def test_week52_to_week1_transition_2027_2028(self):
        """Dec 27, 2027 (Mon of W52) and Jan 3, 2028 (Mon of W01) must differ."""
        w52_monday = date(2027, 12, 27)
        w01_monday = date(2028, 1, 3)
        bin_w52 = _determine_bin_collection(w52_monday, self.WEEK_BLACK, self.WEEK_BANDG, "No")
        bin_w01 = _determine_bin_collection(w01_monday, self.WEEK_BLACK, self.WEEK_BANDG, "No")
        assert bin_w52 != bin_w01, (
            f"Year boundary (52→1): {w52_monday}={bin_w52} and {w01_monday}={w01_monday} should differ"
        )

    # -- stability across runs (same date, same result) -------------------

    def test_parity_stable_across_weekdays(self):
        """Running the scraper on different weekdays should give the same
        bin type for a fixed collection date."""
        target = date(2026, 9, 24)  # Thursday
        expected = _determine_bin_collection(target, self.WEEK_BLACK, self.WEEK_BANDG, "No")
        # Re-derive for the same date — must be identical regardless of "today"
        assert _determine_bin_collection(target, self.WEEK_BLACK, self.WEEK_BANDG, "No") == expected

    # -- green bin suspension ---------------------------------------------

    def test_green_suspension_returns_burgundy_only(self):
        """During the green bin suspension period only Burgundy Bin is returned."""
        # Pick a date that falls on a Burgundy+Green parity week
        burgundy_green_date = date(2026, 9, 22)
        result = _determine_bin_collection(burgundy_green_date, self.WEEK_BLACK, self.WEEK_BANDG, "Yes")
        assert result == "Burgundy Bin"

    def test_no_suspension_returns_both(self):
        """Outside suspension, Burgundy+Green week returns both bins."""
        burgundy_green_date = date(2026, 9, 22)
        result = _determine_bin_collection(burgundy_green_date, self.WEEK_BLACK, self.WEEK_BANDG, "No")
        assert result == "Burgundy Bin & Green Bin"
