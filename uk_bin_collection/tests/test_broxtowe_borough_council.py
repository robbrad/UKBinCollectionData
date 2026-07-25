"""Unit tests for the Broxtowe Borough Council diagnostic helpers.

Broxtowe's form was rebuilt on a new platform (confirmed live via CI's
own integration test against the real site) - the old
ctl00_ContentPlaceHolder1_FF5683* ASP.NET ids are gone, replaced by
semantic ids like FF5683-text/-find/-list. The dropdown's real option
value format is still being determined from live diagnostic output, so
this only covers the diagnostic dump helper for now.
"""

from unittest.mock import MagicMock

from uk_bin_collection.uk_bin_collection.councils.BroxtoweBoroughCouncil import (
    CouncilClass,
)


def fake_option(value: str, text: str, selected: bool = False) -> MagicMock:
    option = MagicMock()
    option.get_attribute.side_effect = lambda name: value if name == "value" else None
    option.text = text
    option.is_selected.return_value = selected
    return option


def test_dump_options_does_not_raise_on_normal_options(capsys):
    select_obj = MagicMock()
    select_obj.options = [
        fake_option("100031320105", "2 Example Street, Nottingham, NG16 2LS"),
        fake_option("100031320106", "4 Example Street, Nottingham, NG16 2LS", True),
    ]

    CouncilClass()._dump_options(select_obj)

    captured = capsys.readouterr()
    assert "100031320105" in captured.out
    assert "Example Street" in captured.out


def test_dump_options_does_not_raise_when_enumeration_fails(capsys):
    # Accessing .options itself raises inside the helper; it should be
    # caught and reported, not propagated.
    broken = MagicMock()
    type(broken).options = property(
        lambda self: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    CouncilClass()._dump_options(broken)

    captured = capsys.readouterr()
    assert "failed to enumerate dropdown options" in captured.out
