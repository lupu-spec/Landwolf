"""Reviewed source definitions. Directory entries never count as ingested records."""

from dataclasses import dataclass
from urllib.parse import urlsplit

from landwolf.states import STATES


@dataclass(frozen=True)
class SourceDefinition:
    id: str
    name: str
    url: str
    states: tuple[str, ...]
    categories: tuple[str, ...]
    coverage_note: str
    automated: bool = True


NATIONWIDE = tuple(STATES)
SOURCES = (
    SourceDefinition(
        "ar_cosl",
        "Arkansas Commissioner of State Lands",
        "https://cosl.org/Home/Contents",
        ("AR",),
        ("tax_sale",),
        "Upcoming county tax-delinquent land sales in the state public-auction catalog. "
        "Canceled entries are excluded. Published taxes are not an asking price or "
        "minimum bid. Post-auction online sales are not included.",
    ),
    SourceDefinition(
        "tx_glo_public",
        "Texas General Land Office",
        "https://www.glo.texas.gov/veterans/land-sale/public",
        ("TX",),
        ("government_land",),
        "Texas GLO public-sale tracts; not county tax-sale inventory.",
    ),
    SourceDefinition(
        "usda_resales",
        "USDA Rural Development / Farm Service Agency",
        "https://www.resales.usda.gov/resales/public/home",
        NATIONWIDE,
        ("foreclosure",),
        "Federal REO and foreclosure listings. Searches all 50 states; current inventory "
        "varies by state. This is not a feed of all mortgage defaults or bank foreclosures.",
    ),
    SourceDefinition(
        "us_treasury",
        "U.S. Treasury real property auctions",
        "https://www.treasury.gov/auctions/treasury/rp/realprop.shtml",
        NATIONWIDE,
        ("public_auction",),
        "Federal seized and forfeited real estate auctions across the US. "
        "These are not county property-tax sales. Dated auctions are hidden after their date.",
    ),
    SourceDefinition(
        "irs_auctions",
        "IRS real estate tax-seizure auctions",
        "https://www.irsauctions.gov/auction/items",
        NATIONWIDE,
        ("tax_sale",),
        "Federal tax-seizure real estate auctions. These are not county tax-deed or "
        "tax-lien certificate inventories. Personal-property auctions are excluded.",
    ),
    SourceDefinition(
        "ak_dnr",
        "Alaska Department of Natural Resources",
        "https://dnr.alaska.gov/mlw/landsales/parcels",
        ("AK",),
        ("government_land",),
        "State DNR over-the-counter land and auctions. Some offerings require Alaska "
        "residency; confirm eligibility, bid deadlines and conditions at the source.",
    ),
    SourceDefinition(
        "mi_dnr",
        "Michigan Department of Natural Resources",
        "https://www.dnr.state.mi.us/landsale",
        ("MI",),
        ("government_land",),
        "General-public BuyNow surplus land. Government/conservancy-only offers "
        "and completed seasonal auctions are excluded.",
    ),
    SourceDefinition(
        "hud_homestore",
        "HUD Home Store",
        "https://www.hudhomestore.gov/",
        NATIONWIDE,
        ("foreclosure",),
        "Browse HUD-owned homes at the official portal. Automated retrieval is not "
        "enabled: the portal disallows crawling. No HUD listings are counted here.",
        False,
    ),
    SourceDefinition(
        "gsa_real_estate",
        "GSA real property disposition",
        "https://disposal.gsa.gov/s/",
        NATIONWIDE,
        ("surplus", "public_auction"),
        "Official federal surplus real-estate portal. Open the source for its current "
        "offerings; this directory link is not an automated listing feed.",
        False,
    ),
    SourceDefinition(
        "mi_tax",
        "Michigan Treasury property-tax foreclosure sales",
        "https://www.michigan.gov/taxes/property/forfeiture-foreclosure",
        ("MI",),
        ("tax_sale",),
        "Official state and county tax-foreclosure information. Follow the relevant "
        "county auction notice for current parcels, sale terms and cancellations.",
        False,
    ),
    SourceDefinition(
        "preforeclosure_records",
        "County records and court notices",
        "https://www.usa.gov/local-governments",
        NATIONWIDE,
        ("pre_foreclosure",),
        "No nationwide pre-foreclosure feed is connected. Use the county recorder "
        "or court to confirm notices and case status. A default notice is not an "
        "offer to sell, an auction date, or proof the owner will lose the property.",
        False,
    ),
)
SOURCE_BY_ID = {source.id: source for source in SOURCES}


def matches(source: SourceDefinition, state: str, category: str, source_id: str | None) -> bool:
    return (
        (state == "US" or state in source.states)
        and (category == "all" or category in source.categories)
        and (source_id is None or source.id == source_id)
    )


def safe_link(url: str) -> bool:
    """Allow only reviewed HTTPS source hosts; never use this to authorize HTTP fetching."""
    try:
        parts = urlsplit(url)
        hosts = {urlsplit(source.url).hostname for source in SOURCES} | {"www.usa.gov"}
        return bool(
            parts.scheme == "https"
            and parts.hostname in hosts
            and not parts.username
            and not parts.password
            and parts.port is None
            and len(url) <= 1000
        )
    except ValueError:
        return False
