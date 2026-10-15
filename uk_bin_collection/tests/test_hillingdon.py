"""Offline tests for Hillingdon's XFP form flow (markup reduced from live CI captures)."""

from unittest.mock import MagicMock, patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import Hillingdon

PC = "q19086cfd700db258ce784ccedfba383d7aa05ffb"
CALLBACK = '{"action":"ic","element":"%s","data":0,"tableRow":-1}' % PC


def form(inner, token="t1"):
    return f"""<html><body><form class="form" method="post" action="/xfp/form/379">
    <input type="hidden" name="__token" value="{token}">
    <input type="hidden" name="page" value="2361"><input type="hidden" name="locale" value="en_GB">
    <input class="form__field" id="{PC}_0_0" type="text" name="{PC}_0_0" autocomplete="postal-code">
    <button type="submit" name="callback" value='{CALLBACK}' class="button btn--lookup">Lookup</button>
    {inner}</form></body></html>"""


ADDRESSES = f"""<select class="form__select" id="{PC}_1_0" name="{PC}_1_0">
<option value="">Please choose...</option>
<option value="100021488480">1 Milverton Drive, Ickenham, UB10 8PP</option>
<option value="100021488481">2 Milverton Drive, Ickenham, UB10 8PP</option>
<option value="10022801130">2a Milverton Drive, Ickenham, UB10 8PP</option>
<option value="100021488491">12 Milverton Drive, Ickenham, UB10 8PP</option>
</select><button class="button button--primary" type="submit" name="next" value="Next">Next</button>"""

DETAILS = """<html><body><form method="post" action="/xfp/form/379">
<label class="form__label" for="qd53">Date</label>
<input class="form__field" id="qd53" type="text" name="qd53" value="&quot;Tuesday 20-10-2026&quot;">
<label class="form__label" for="qdc6"> Types of containers</label>
<input class="form__field" id="qdc6" type="text" name="qdc6" value="&quot;Recycling, Household, Food\\n&quot;">
<div>Next collection</div><div>Tuesday 20th October</div></form></body></html>"""

OPTIONS = [
    ("100021488480", "1 Milverton Drive, Ickenham, UB10 8PP"),
    ("100021488481", "2 Milverton Drive, Ickenham, UB10 8PP"),
    ("10022801130", "2a Milverton Drive, Ickenham, UB10 8PP"),
    ("100021488491", "12 Milverton Drive, Ickenham, UB10 8PP"),
]


@pytest.mark.parametrize(
    "paon, uprn, expected",
    [
        (
            "1, Milverton Drive, Ickenham, UB10 8PP, Ickenham, Hillingdon",
            None,
            "100021488480",
        ),
        ("2a", None, "10022801130"),
        ("1", None, "100021488480"),
        ("12 Milverton Drive", None, "100021488491"),
        (None, "100021488481", "100021488481"),
    ],
    ids=[
        "old-full-address",
        "flat-letter",
        "number-not-prefix-of-12",
        "number-and-street",
        "uprn",
    ],
)
def test_choose_address(paon, uprn, expected):
    assert Hillingdon._choose_address(OPTIONS, paon, uprn) == expected


def test_unknown_address_is_an_error():
    with pytest.raises(ValueError, match="Could not match address '99'"):
        Hillingdon._choose_address(OPTIONS, "99", None)


def test_full_flow_posts_lookup_then_address_and_parses_results():
    session = MagicMock()
    start = MagicMock(text=form(""), url="https://pre.hillingdon.gov.uk/xfp/form/379")
    session.get.return_value = start
    session.post.side_effect = [
        MagicMock(text=form(ADDRESSES, token="t2")),
        MagicMock(text=DETAILS),
    ]
    with patch.object(
        Hillingdon.requests, "Session", return_value=session
    ), patch.object(Hillingdon, "check_postcode", return_value=True):
        data = Hillingdon.CouncilClass().parse_data(
            "",
            postcode="UB10 8PP",
            paon="1, Milverton Drive, Ickenham, UB10 8PP, Ickenham, Hillingdon",
        )

    lookup, choose = session.post.call_args_list
    assert lookup.args[0] == "https://pre.hillingdon.gov.uk/xfp/form/379"
    assert lookup.kwargs["data"]["callback"] == CALLBACK
    assert lookup.kwargs["data"][f"{PC}_0_0"] == "UB10 8PP"
    assert choose.kwargs["data"]["__token"] == "t2"
    assert choose.kwargs["data"][f"{PC}_1_0"] == "100021488480"
    assert choose.kwargs["data"]["next"] == "Next"
    assert data == {
        "bins": [
            {"type": "Recycling", "collectionDate": "20/10/2026"},
            {"type": "Household", "collectionDate": "20/10/2026"},
            {"type": "Food", "collectionDate": "20/10/2026"},
        ]
    }
