"""Carmarthenshire reads every container from the council's recycling checker."""

from unittest.mock import MagicMock, patch

import pytest

from uk_bin_collection.uk_bin_collection.councils import CarmarthenshireCountyCouncil

# The public test UPRN from input.json. The council's answer is mocked, so the
# same UPRN serves both pages below.
TEST_UPRN = "10004859302"

# GetRecyclingInfo for the input.json UPRN on 2026-11-19: a property still on the
# blue-bag service.
BLUE_BAG_SERVICE_PAGE = """
<h2 class="text-center font15 recHeader">You next recycling and waste collection</h2>
<div class="clearfix">
            <div class="col-lg-3 col-md-3 col-sm-3 col-xs-6 recycling-outer-container">
                <p class="text-center"><img src="/media/4g3pizuc/waste-widget_black-bag.png" alt="" height="100"></p>
                <p class="text-center">
                    Black bags<br />
                    <strong>Wednesday</strong><br />
                    <strong>09/12/2026</strong><br />
                    <a target="_blank" href="https://www.carmarthenshire.gov.wales/media/h5dngpx3/w2bg-english.pdf" class="underline"><span class="fas fa-cloud-download-alt"></span> Download your collections calendar</a>
                </p>
            </div>
            <div class="col-lg-3 col-md-3 col-sm-3 col-xs-6 recycling-outer-container">
                <p class="text-center"><img src="/media/ubbilmyb/waste-widget_blue-bag.png" alt="" height="100"></p>
                <p class="text-center">
                    Blue bags<br />
                    <strong>Friday</strong><br />
                    <strong>20/11/2026</strong><br />
                    <span class="far fa-calendar-alt"></span> Collected every week
                </p>
            </div>
            <div class="col-lg-3 col-md-3 col-sm-3 col-xs-6 recycling-outer-container">
                <p class="text-center"><img src="/media/xcbgpzgm/sr-96936-food-waste_t280x190.png" alt="" height="100"></p>
                <p class="text-center">
                    Food waste bin<br />
                    <strong>Friday</strong><br />
                    <strong>20/11/2026</strong><br />
                    <span class="far fa-calendar-alt"></span> Collected every week
                </p>
            </div>
                <div class="col-lg-3 col-md-3 col-sm-3 col-xs-6 recycling-outer-container">
                    <p class="text-center"><img src="/media/mzsbpyuu/sr-96936-black-box_t280x190.png" alt="" height="100"></p>
                    <p class="text-center">
                        Black box<br />
                        (Glass bottles and jars)<br />

                             <strong>Wednesday</strong><br />
                             <strong>09/12/2026</strong><br />
                            <a target="_blank" href="https://www.carmarthenshire.gov.wales/media/h5dngpx3/w2bg-english.pdf" class="underline"><span class="fas fa-cloud-download-alt"></span> Download your collections calendar</a>
                    </p>
                </div>
</div>
    <div class="alert alert-info">
        Place your containers at your collection point before 6am on your collection day.
    </div>
<div class="garden-waste-container hidden">
    <h2 class="text-center font15 recHeader">Garden waste</h2>
    <div class="clearfix">
        <div class="col-lg-offset-3 col-md-offset-3 col-sm-offset-3 col-xs-offset-0 col-lg-3 col-md-3 col-sm-3 col-xs-6 recycling-outer-container">
            <p class="text-center"><img src="/media/gg4lh3si/waste-widget_garden-waste.png" alt="" height="100"></p>
        </div>
        <div class="col-lg-6 col-md-6 col-sm-6 col-xs-6 recycling-outer-container">
            <p>
                <strong>Thursday</strong><br />
                <strong>26/11/2026</strong><br />
                <strong>Week:  Brown</strong><br />
                <a target="_blank" href="https://www.carmarthenshire.gov.wales/media/50un5pi0/sr-87825_calendarsgarden2026_english.pdf" class="underline"><span class="fas fa-cloud-download-alt"></span> Download your garden waste collections calendar (.pdf)</a>  and follow the correct colour for your area.
            </p>
        </div>

    </div>
        <div class="alert alert-info">
            This is a chargeable collections service.  <a href="https://www.carmarthenshire.gov.wales/home/council-services/recycling-bins-and-litter/garden-waste" class="underline">Find out more information and how to apply.</a>
        </div>
</div>

<div class="nappy-waste-container hidden">
    <h2 class="text-center font15 recHeader">Hygiene and nappy waste</h2>
    <div class="clearfix">
        <div class="col-lg-offset-3 col-md-offset-3 col-sm-offset-3 col-xs-offset-0 col-lg-3 col-md-3 col-sm-3 col-xs-6 recycling-outer-container">
            <p class="text-center"><img src="/media/2smo4dpj/waste-widget_purple-bag.png" alt="" height="100"></p>
        </div>
        <div class="col-lg-6 col-md-6 col-sm-6 col-xs-6 recycling-outer-container">
            <p>
                <strong>Thursday</strong><br />
                <strong>26/11/2026</strong><br />


                    <a target="_blank" href="https://www.carmarthenshire.gov.wales/media/cw3d52dp/sr-87830_calendarsahp2026_w1_english.pdf" class="underline"><span class="fas fa-cloud-download-alt"></span> Download your hygiene and nappy waste collections calendar (.pdf) </a>
            </p>
        </div>

    </div>
        <div class="alert alert-info">
            You must <a href="https://myaccount.carmarthenshire.gov.wales/en/service/Hygiene_And_Nappy_Waste_Service" class="underline">apply to receive a hygiene collection</a>. This is a free collections service. <a href="https://www.carmarthenshire.gov.wales/home/council-services/recycling-bins-and-litter/hygiene-and-nappy-waste/" class="underline">Find out more about hygiene collections.</a>
        </div>

</div>
"""

# GetRecyclingInfo on 2026-11-19 for a home on the separated recycling service
# that started on 2 November 2026. The page carries no address, and its round
# identifiers (garden week colour, calendar file names) are replaced with neutral
# placeholders.
SEPARATED_RECYCLING_PAGE = """
<h2 class="text-center font15 recHeader">Your next recycling and waste collection</h2>
<div class="clearfix">
        <div class="col-lg-3 col-md-3 col-sm-3 col-xs-6 recycling-outer-container">
            <p class="text-center"><img src="/media/4g3pizuc/waste-widget_black-bag.png" alt="" height="100"></p>
            <p class="text-center">
                Black bag<br />

                <strong>Thursday</strong><br />
                <strong>26/11/2026</strong><br />
                <a target="_blank" href="https://www.carmarthenshire.gov.wales/media/calendar/collections-english.pdf" class="underline"><span class="fas fa-cloud-download-alt"></span> Download your collections calendar</a>
            </p>
        </div>
    <div class="col-lg-3 col-md-3 col-sm-3 col-xs-6 recycling-outer-container">
        <p class="text-center"><img src="/media/xcbgpzgm/sr-96936-food-waste_t280x190.png" alt="" height="100"></p>
        <p class="text-center">
            Food waste bin<br />
            <strong>Wednesday</strong><br />
            <strong>25/11/2026</strong><br />
            <span class="far fa-calendar-alt"></span> Collected every week
        </p>
    </div>
    <div class="col-lg-3 col-md-3 col-sm-3 col-xs-6 recycling-outer-container">
        <p class="text-center"><img src="/media/edfbnerd/sr-96936-blue-sack_t280x190.png" alt="" height="100"></p>
        <p class="text-center">
            Blue sack<br />
            (Paper)<br />
            <strong>Wednesday</strong><br />
            <strong>25/11/2026</strong><br />
            <span class="far fa-calendar-alt"></span> Collected every week
        </p>
    </div>
    <div class="col-lg-3 col-md-3 col-sm-3 col-xs-6 recycling-outer-container">
        <p class="text-center"><img src="/media/2eyp1pnc/sr-96936-orange-sack_t280x190.png" alt="" height="100"></p>
        <p class="text-center">
            Orange sack<br />
            (Cardboard)<br />
            <strong>Wednesday</strong><br />
            <strong>25/11/2026</strong><br />
            <span class="far fa-calendar-alt"></span> Collected every week
        </p>
    </div>


</div>
<div class="clearfix">
        <div class="col-lg-3 col-md-3 col-sm-3 col-xs-6 recycling-outer-container">
            <p class="text-center"><img src="/media/sfqhvsej/sr-96936-red-sack_t280x190-b.png" alt="" height="100"></p>
            <p class="text-center">
                Red sack<br />
                (Metals, plastics and cartons)<br />
                <strong>Wednesday</strong><br />
                <strong>25/11/2026</strong><br />
                <span class="far fa-calendar-alt"></span> Collected every week
            </p>
        </div>
    <div class="col-lg-3 col-md-3 col-sm-3 col-xs-6 recycling-outer-container">
        <p class="text-center"><img src="/media/wnspds1z/sr-96936-red-bag_t280x190.png" alt="" height="100"></p>
        <p class="text-center">
            Single-use red bags <br />
            (Plastic bags and wrapping. - when your bag is full, tie it securely, then put it inside your red sack)<br />
            <strong>Wednesday</strong><br />
            <strong>25/11/2026</strong><br />
            <span class="far fa-calendar-alt"></span> Collected every week
        </p>
    </div>
    <div class="col-lg-3 col-md-3 col-sm-3 col-xs-6 recycling-outer-container">
        <p class="text-center"><img src="/media/5q2mflz4/sr-96936-white-sack_t280x190.png" alt="" height="100"></p>
        <p class="text-center">
            Small white sack<br />
            (Household batteries)<br />
            <strong>Wednesday</strong><br />
            <strong>25/11/2026</strong><br />
            <span class="far fa-calendar-alt"></span> Collected every week
        </p>
    </div>

    <div class="col-lg-3 col-md-3 col-sm-3 col-xs-6 recycling-outer-container">
        <p class="text-center"><img src="/media/mzsbpyuu/sr-96936-black-box_t280x190.png" alt="" height="100"></p>
        <p class="text-center">
            Black box<br />
                (Glass bottles and jars)<br/>
                <strong>Wednesday</strong><br />
                <strong>25/11/2026</strong><br />
                <span class="far fa-calendar-alt"></span> Collected every week
        </p>
    </div>


    </div>
    <div class="alert alert-info">
        Place your containers at your collection point before 6am on your collection day.
    </div>
<div class="garden-waste-container hidden">
    <h2 class="text-center font15 recHeader">Garden waste</h2>
    <div class="clearfix">
        <div class="col-lg-offset-3 col-md-offset-3 col-sm-offset-3 col-xs-offset-0 col-lg-3 col-md-3 col-sm-3 col-xs-6 recycling-outer-container">
            <p class="text-center"><img src="/media/gg4lh3si/waste-widget_garden-waste.png" alt="" height="100"></p>
        </div>
        <div class="col-lg-6 col-md-6 col-sm-6 col-xs-6 recycling-outer-container">
            <p>
                <strong>Monday</strong><br />
                <strong>30/11/2026</strong><br />
                <strong>Week: Colour</strong><br />
                <a target="_blank" href="https://www.carmarthenshire.gov.wales/media/calendar/garden-english.pdf" class="underline"><span class="fas fa-cloud-download-alt"></span> Download your garden waste collections calendar (.pdf) </a> and follow the correct colour for your area.
            </p>
        </div>

    </div>

        <div class="alert alert-info">
            This is a chargeable collections service.  <a href="https://www.carmarthenshire.gov.wales/home/council-services/recycling-bins-and-litter/garden-waste" class="underline">Find out more information and how to apply.</a>
        </div>
</div>


<div class="nappy-waste-container hidden">
    <h2 class="text-center font15 recHeader">Hygiene and nappy waste</h2>
    <div class="clearfix">
        <div class="col-lg-offset-3 col-md-offset-3 col-sm-offset-3 col-xs-offset-0 col-lg-3 col-md-3 col-sm-3 col-xs-6 recycling-outer-container">
            <p class="text-center"><img src="/media/2smo4dpj/waste-widget_purple-bag.png" alt="" height="100"></p>
        </div>
        <div class="col-lg-6 col-md-6 col-sm-6 col-xs-6 recycling-outer-container">
            <p>
                <strong>Tuesday</strong><br />
                <strong>01/12/2026</strong><br />

                    <a target="_blank" href="https://www.carmarthenshire.gov.wales/media/calendar/hygiene-english.pdf" class="underline"><span class="fas fa-cloud-download-alt"></span> Download your hygiene and nappy waste collections calendar (.pdf) </a>
            </p>
        </div>

    </div>


            <div class="alert alert-info">
            You must <a href="https://myaccount.carmarthenshire.gov.wales/en/service/Hygiene_And_Nappy_Waste_Service" class="underline">apply to receive a hygiene collection</a>. This is a free collections service. <a href="https://www.carmarthenshire.gov.wales/home/council-services/recycling-bins-and-litter/hygiene-and-nappy-waste/" class="underline">Find out more about hygiene collections.</a>
            </div>


</div>
"""


def _parse(page):
    response = MagicMock(content=page.encode())
    with patch.object(
        CarmarthenshireCountyCouncil.requests, "get", return_value=response
    ) as get:
        result = CarmarthenshireCountyCouncil.CouncilClass().parse_data(
            "", uprn=TEST_UPRN
        )
    return result, get


def test_it_asks_the_recycling_checker_for_the_uprn():
    _, get = _parse(BLUE_BAG_SERVICE_PAGE)

    assert get.call_args.args[0].endswith(
        "/SurfaceKerbsiteRecyclingChecker/GetRecyclingInfo/"
    )
    assert get.call_args.kwargs["params"]["uprn"] == TEST_UPRN
    assert get.call_args.kwargs["timeout"]
    assert get.call_args.kwargs["headers"]["User-Agent"].startswith("Mozilla/5.0")


def test_a_blue_bag_service_home_gets_every_container():
    result, _ = _parse(BLUE_BAG_SERVICE_PAGE)

    assert result["bins"] == [
        {"type": "Blue bags", "collectionDate": "20/11/2026"},
        {"type": "Food waste bin", "collectionDate": "20/11/2026"},
        {"type": "Garden waste", "collectionDate": "26/11/2026"},
        {"type": "Hygiene and nappy waste", "collectionDate": "26/11/2026"},
        {"type": "Black bags", "collectionDate": "09/12/2026"},
        {"type": "Black box", "collectionDate": "09/12/2026"},
    ]


def test_a_separated_recycling_home_gets_recycling_food_and_glass():
    # Issue #2329: the old page left these homes with an empty blue-bag date
    # and nothing for recycling, food or glass.
    result, _ = _parse(SEPARATED_RECYCLING_PAGE)

    assert result["bins"] == [
        {"type": "Food waste bin", "collectionDate": "25/11/2026"},
        {"type": "Blue sack", "collectionDate": "25/11/2026"},
        {"type": "Orange sack", "collectionDate": "25/11/2026"},
        {"type": "Red sack", "collectionDate": "25/11/2026"},
        {"type": "Single-use red bags", "collectionDate": "25/11/2026"},
        {"type": "Small white sack", "collectionDate": "25/11/2026"},
        {"type": "Black box", "collectionDate": "25/11/2026"},
        {"type": "Black bag", "collectionDate": "26/11/2026"},
        {"type": "Garden waste", "collectionDate": "30/11/2026"},
        {"type": "Hygiene and nappy waste", "collectionDate": "01/12/2026"},
    ]


def test_a_container_without_a_date_is_skipped():
    page = BLUE_BAG_SERVICE_PAGE.replace(
        "<strong>20/11/2026</strong>", "<strong></strong>"
    )

    result, _ = _parse(page)

    types = [bin_["type"] for bin_ in result["bins"]]
    assert "Blue bags" not in types
    assert "Food waste bin" not in types
    assert "Black bags" in types


def test_a_page_with_no_collections_is_a_clear_error():
    with pytest.raises(ValueError, match="no collections for UPRN 10004859302"):
        _parse("<h2>Your next recycling and waste collection</h2>")
