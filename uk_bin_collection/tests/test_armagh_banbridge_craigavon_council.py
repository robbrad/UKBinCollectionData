from unittest.mock import MagicMock, patch

from uk_bin_collection.uk_bin_collection.councils.ArmaghBanbridgeCraigavonCouncil import (
    CouncilClass,
)

PAGE = """
<div class="heading bg-black">Domestic</div>
<div class="col-sm-12 col-md-9"><h4>Friday 30/10/2026</h4><h4>Friday 13/11/2026</h4></div>
<div class="heading bg-green">Recycling</div>
<div class="col-sm-12 col-md-9"><h4>Friday 23/10/2026</h4><h4>No date yet</h4></div>
<div class="heading bg-brown">Garden</div>
<div class="col-sm-12 col-md-9"><h4>06/11/2026</h4></div>
"""


def test_dates_with_a_weekday_prefix_are_parsed_and_sorted():
    response = MagicMock(text=PAGE)
    with patch("requests.Session.get", return_value=response):
        data = CouncilClass().parse_data("", uprn="185625284")
    assert data["bins"] == [
        {"collectionDate": "23/10/2026", "type": "Recycling"},
        {"collectionDate": "30/10/2026", "type": "Domestic"},
        {"collectionDate": "06/11/2026", "type": "Garden"},
        {"collectionDate": "13/11/2026", "type": "Domestic"},
    ]
