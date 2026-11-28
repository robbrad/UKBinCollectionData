"""Unit tests for the shared Salesforce property flow used by Cotswold,
Forest of Dean, West Oxfordshire and Guildford (address choice and dates)."""

from datetime import date

import pytest

from uk_bin_collection.uk_bin_collection.salesforce_property_flow import (
    AddressNotFoundError,
    AmbiguousAddressError,
    build_bins,
    build_search_address,
    parse_collection_day,
    select_address_option,
)

TODAY = date(2026, 11, 28)


def _options(*addresses: str) -> list[dict]:
    return [{"address": a, "value": str(i)} for i, a in enumerate(addresses)]


class TestSelectAddressOption:
    def test_house_number_matches_only_whole_number(self):
        options = _options(
            "124 HIGH STREET, WITNEY, OX28 1YA",
            "24A HIGH STREET, WITNEY, OX28 1YA",
            "24 HIGH STREET, WITNEY, OX28 1YA",
        )
        assert select_address_option(options, "24", "OX28 1YA")["value"] == "2"

    def test_full_address_in_house_number(self):
        options = _options(
            "19 SUMMERS WAY, MORETON-IN-MARSH, GL56 0GB",
            "190 SUMMERS WAY, MORETON-IN-MARSH, GL56 0GB",
        )
        chosen = select_address_option(
            options, "19 SUMMERS WAY, MORETON-IN-MARSH, GL56 0GB", "GL56 0GB"
        )
        assert chosen["value"] == "0"

    def test_house_name_is_not_a_substring_match(self):
        options = _options(
            "GREYS LODGE, PUTTENHAM HILL, GU3 1AH",
            "THE LODGE, PUTTENHAM HILL HOUSE, GU3 1AH",
        )
        assert select_address_option(options, "THE LODGE", "GU3 1AH")["value"] == "1"

    def test_no_match_raises_and_lists_candidates(self):
        options = _options("25 HIGH STREET, OX28 1YA")
        with pytest.raises(AddressNotFoundError, match="25 HIGH STREET"):
            select_address_option(options, "24", "OX28 1YA")

    def test_wrong_postcode_does_not_match(self):
        options = _options("24 HIGH STREET, OX28 1YB")
        with pytest.raises(AddressNotFoundError):
            select_address_option(options, "24", "OX28 1YA")

    def test_several_matches_raise_rather_than_guess(self):
        options = _options("24 HIGH STREET, OX28 1YA", "24 HIGH LANE, OX28 1YA")
        with pytest.raises(AmbiguousAddressError, match="HIGH LANE"):
            select_address_option(options, "24", "OX28 1YA")

    def test_blank_house_number_raises(self):
        with pytest.raises(AddressNotFoundError):
            select_address_option(_options("24 HIGH STREET, OX28 1YA"), " ", "OX28 1YA")


class TestBuildSearchAddress:
    def test_appends_postcode(self):
        assert build_search_address("24", "OX28 1YA") == "24, OX28 1YA"

    def test_does_not_repeat_a_postcode_already_present(self):
        full = "19 SUMMERS WAY, MORETON-IN-MARSH, GL56 0GB"
        assert build_search_address(full, "GL56 0GB") == full


class TestParseCollectionDay:
    def test_abbreviated_weekday(self):
        assert parse_collection_day("Mon, 30 November", TODAY) == "30/11/2026"

    def test_full_weekday(self):
        assert parse_collection_day("Monday, 7 December", TODAY) == "07/12/2026"

    def test_today_and_tomorrow(self):
        assert parse_collection_day("Today", TODAY) == "28/11/2026"
        assert parse_collection_day("Tomorrow", TODAY) == "29/11/2026"

    def test_past_date_rolls_to_next_year(self):
        assert parse_collection_day("Thu, 2 January", TODAY) == "02/01/2027"

    def test_today_itself_stays_this_year(self):
        assert parse_collection_day("Sat, 28 November", TODAY) == "28/11/2026"

    def test_29_february_resolves_in_a_leap_year(self):
        assert parse_collection_day("Tue, 29 February", date(2027, 12, 1)) == (
            "29/02/2028"
        )

    def test_not_a_date_raises(self):
        with pytest.raises(ValueError):
            parse_collection_day("Not collected", TODAY)


class TestBuildBins:
    def test_builds_bins(self):
        result = build_bins([("Blue Bag", "Mon, 30 November")], TODAY)
        assert result == {
            "bins": [{"type": "Blue Bag", "collectionDate": "30/11/2026"}]
        }

    def test_skips_non_date_rows_but_keeps_the_rest(self):
        rows = [("Garden Bin", "Not subscribed"), ("Blue Bag", "Mon, 30 November")]
        assert [b["type"] for b in build_bins(rows, TODAY)["bins"]] == ["Blue Bag"]

    def test_no_dates_raises_instead_of_returning_empty(self):
        with pytest.raises(ValueError, match="No collection dates"):
            build_bins([("Garden Bin", "Not subscribed")], TODAY)
        with pytest.raises(ValueError):
            build_bins([], TODAY)
