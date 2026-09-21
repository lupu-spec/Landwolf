"""Synthetic MnDOT pages exercise published units, dates and fail-closed contracts."""

import pytest

from landwolf.minnesota import parse_minnesota
from landwolf.national import approved_url
from landwolf.provider import SourceUnavailable

BID = """<h3>Current properties for sale by bid</h3><ul><li>
<a
href="https://edocs-public.dot.state.mn.us/edocs_public/DMResultSet/download?docId=99999"
>Sale 99999</a>
(PDF) - 5.03 Acres of Vacant Land located at 123 Fixture Road, Test City, Fixture County, MN.
<strong>*Bid Opening September 30, 2099</strong></li></ul><p>Last Update: August 7, 2099</p>"""
OTC = BID.replace("Current properties for sale by bid", "Properties currently available").replace(
    "5.03 Acres", "43,560 Square Feet"
)


def test_published_sale_and_unknown_pdf_only_values():
    item = parse_minnesota(BID, by_bid=True)[0]
    assert item.state == "MN" and item.county == "Fixture"
    assert item.asking_price is None and item.parcel_number is None
    assert item.latitude is None and item.longitude is None
    assert item.price_kind == "Not published" and item.acres == 5.03
    assert item.auction_date.isoformat() == "2099-09-30"
    assert item.source_effective_date.isoformat() == "2099-08-07"


def test_immediate_sale_unit_conversion_is_explicit():
    item = parse_minnesota(OTC, by_bid=False)[0]
    assert item.acres == 1 and item.acreage_basis == "calculated"
    assert item.sale_status == "Available" and item.auction_date is None


@pytest.mark.parametrize("change", ["Sold", "Canceled"])
def test_cancelled_and_sold_not_active(change):
    assert not parse_minnesota(BID.replace("(PDF)", change), by_bid=True)[0].active


def test_past_event_not_active():
    assert not parse_minnesota(
        BID.replace("September 30, 2099", "September 30, 2000"), by_bid=True
    )[0].active


@pytest.mark.parametrize(
    "original,replacement",
    [
        ("Current properties for sale by bid", "Unrecognized inventory"),
        ("docId=99999", "docId=99999&redirect=evil"),
        ("edocs-public.dot.state.mn.us", "evil.example"),
        ("5.03 Acres", "unknown area"),
        ("Bid Opening September 30, 2099", "Date pending"),
    ],
)
def test_layout_and_url_changes_fail_closed(original, replacement):
    with pytest.raises(SourceUnavailable):
        parse_minnesota(BID.replace(original, replacement), by_bid=True)


def test_only_reviewed_minnesota_pages_can_be_fetched():
    assert approved_url("mn_dot", "https://www.dot.state.mn.us/row/propsales.html")
    for url in [
        "https://www.dot.state.mn.us/row/propsales.html?url=http://127.0.0.1",
        "http://www.dot.state.mn.us/row/propsales.html",
        "https://www.dot.state.mn.us.evil.example/row/propsales.html",
    ]:
        assert not approved_url("mn_dot", url)
