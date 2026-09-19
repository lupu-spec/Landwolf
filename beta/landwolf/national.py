"""Bounded adapters for public government inventories; no browser or private APIs."""

import asyncio
import re
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup, Tag

from landwolf.minnesota import PAGES, parse_minnesota
from landwolf.provider import SourceUnavailable, stamp
from landwolf.schemas import PropertyRecord
from landwolf.sources import SOURCE_BY_ID
from landwolf.states import STATES

MAX_INVENTORY = 5000
MAX_REQUESTS = 240
MAX_RESPONSE_BYTES = 8_000_000
USDA = "https://www.resales.usda.gov"
IRS = "https://www.irsauctions.gov"
TREASURY = "https://www.treasury.gov/auctions/treasury/rp/"
ALASKA = "https://dnr.alaska.gov"
MICHIGAN = "https://www.dnr.state.mi.us"
ARKANSAS = "https://cosl.org"


def approved_url(source: str, url: str) -> bool:
    """Exact host/path/query contracts; redirects and user-selected URLs are prohibited."""
    try:
        p = urlsplit(url)
        if p.scheme != "https" or p.username or p.password or p.port or p.fragment:
            return False
        query = parse_qs(p.query, keep_blank_values=True)
        if source == "ar_cosl" and p.netloc == "cosl.org":
            if p.path == "/Home/Contents":
                return not query
            return bool(
                p.path == "/Home/CatalogViewBySaleDate"
                and set(query) == {"saledate"}
                and len(query["saledate"]) == 1
                and re.fullmatch(
                    r"\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2} [AP]M", query["saledate"][0]
                )
            )
        if source == "usda_resales" and p.netloc == "www.resales.usda.gov":
            if re.fullmatch(r"/resales/public/search(SFH|MFH|FSA)", p.path):
                return not query
            return bool(
                re.fullmatch(r"/resales/public/(SFH|MFH|FSA)PropertyDetail", p.path)
                and set(query) == {"id", "listingType"}
                and len(query["id"]) == len(query["listingType"]) == 1
                and re.fullmatch(r"\d{1,12}", query["id"][0])
                and query["listingType"][0] in {"Foreclosure", "REO Property"}
            )
        if source == "irs_auctions" and p.netloc == "www.irsauctions.gov":
            if re.fullmatch(r"/ad/[a-z0-9-]{1,200}", p.path):
                return not query
            return bool(
                p.path == "/auction/items"
                and set(query)
                <= {"page", "field_asset_type_target_id", "field_sale_type_target_id"}
                and query.get("field_asset_type_target_id") == ["8"]
                and query.get("field_sale_type_target_id") == ["1"]
                and re.fullmatch(r"\d{1,2}", query.get("page", ["0"])[0])
                and all(len(value) == 1 for value in query.values())
            )
        if source == "us_treasury" and p.netloc == "www.treasury.gov":
            return bool(
                re.fullmatch(r"/auctions/treasury/rp/[a-z0-9_-]+\.shtml", p.path) and not query
            )
        if source == "ak_dnr" and p.netloc == "dnr.alaska.gov":
            return p.path in {"/mlw/landsales/", "/mlw/landsales/parcels"} and not query
        if source == "mi_dnr" and p.netloc == "www.dnr.state.mi.us":
            return p.path == "/LandSale/Parcels/PublicSearch" and not query
        if source == "mn_dot":
            return url in PAGES
    except ValueError:
        return False
    return False


class PublicReader:
    def __init__(self, source: str, client: httpx.AsyncClient) -> None:
        self.source, self.client, self.requests = source, client, 0

    async def read(self, url: str, data: dict[str, str] | None = None) -> str:
        for attempt in range(2):
            try:
                return await self._read(url, data)
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt:
                    raise
            except httpx.HTTPStatusError as exc:
                if attempt or exc.response.status_code not in {429, 502, 503, 504}:
                    raise
            await asyncio.sleep(0.5)
        raise SourceUnavailable("Public source did not respond")

    async def _read(self, url: str, data: dict[str, str] | None) -> str:
        self.requests += 1
        if self.requests > MAX_REQUESTS or not approved_url(self.source, url):
            raise SourceUnavailable("Source request limit or URL contract failed")
        async with self.client.stream("POST" if data is not None else "GET", url, data=data) as r:
            r.raise_for_status()
            if "text/html" not in r.headers.get("content-type", "").lower():
                raise SourceUnavailable("Source did not return HTML")
            body = bytearray()
            async for chunk in r.aiter_bytes():
                body.extend(chunk)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise SourceUnavailable("Source response exceeded size limit")
            return body.decode(r.encoding or "utf-8")


def text(node: Tag | None) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node is not None else ""


def required_match(pattern: str, value: str) -> re.Match[str]:
    match = re.search(pattern, value, re.IGNORECASE)
    if match is None:
        raise SourceUnavailable("Source field layout changed")
    return match


def number(value: str) -> float:
    normalized = value.strip().replace(",", "").replace("$", "")
    if not re.fullmatch(r"\d+(?:\.\d+)?", normalized):
        raise SourceUnavailable("Invalid published numeric field")
    return float(normalized)


def record(source: str, **fields: Any) -> PropertyRecord:
    definition = SOURCE_BY_ID[source]
    return PropertyRecord(
        source=source,
        source_name=definition.name,
        retrieved_at=stamp(),
        data_completeness=40,
        **fields,
    )


def checked(records: list[PropertyRecord]) -> list[PropertyRecord]:
    if len(records) > MAX_INVENTORY or len({r.id for r in records}) != len(records):
        raise SourceUnavailable("Inventory too large or contains duplicate identifiers")
    return records


def arkansas_catalog(html: str, today: date) -> list[tuple[str, date]]:
    soup = BeautifulSoup(html, "html.parser")
    if "Public Auction Catalog" not in text(soup) or "Sale Date" not in text(soup):
        raise SourceUnavailable("Arkansas auction index layout changed")
    result: dict[str, date] = {}
    for anchor in soup.select('a[href*="CatalogViewBySaleDate"]'):
        url = urljoin(ARKANSAS, str(anchor["href"]))
        if not approved_url("ar_cosl", url):
            raise SourceUnavailable("Arkansas catalog URL contract failed")
        day = datetime.strptime(
            parse_qs(urlsplit(url).query)["saledate"][0], "%m/%d/%Y %I:%M:%S %p"
        ).date()
        if day >= today:
            result[url] = day
    if len(result) > 75:
        raise SourceUnavailable("Arkansas catalog exceeded expected size")
    return list(result.items())


def parse_arkansas(html: str, url: str, day: date) -> list[PropertyRecord]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("#tableAllCertifications")
    if table is None or [text(h) for h in table.select("thead th")] != [
        "County",
        "Sale #",
        "Name",
        "Legal Description",
        "Interested Parties",
        "Parcel #",
        "Taxes",
        "Actions",
    ]:
        raise SourceUnavailable("Arkansas parcel table layout changed")
    result: list[PropertyRecord] = []
    for row in table.select("tbody tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) != 8:
            raise SourceUnavailable("Arkansas parcel columns changed")
        if text(cells[2]) == "ENTRY CANCELLED":
            continue
        county, sale_id, parcel = text(cells[0]), text(cells[1]), text(cells[5])
        if (
            not re.fullmatch(r"[A-Z ]{1,50}", county)
            or not re.fullmatch(r"\d{1,12}", sale_id)
            or not parcel
        ):
            raise SourceUnavailable("Arkansas parcel identifier invalid")
        description = text(cells[3])
        item = record(
            "ar_cosl",
            id=f"ar-cosl-{day.year}-{county.lower().replace(' ', '-')}-{sale_id}",
            tract=parcel,
            parcel_number=parcel,
            title="Tax-sale parcel " + parcel,
            state="AR",
            county=county.title(),
            source_url=url,
            category="tax_sale",
            sale_type="County tax-delinquent land auction",
            sale_status="Auction scheduled",
            auction_date=day,
            reported_taxes=number(text(cells[6])) if text(cells[6]) else None,
            legal_description=description[:6000] or None,
        )
        item.risk_notes.extend(
            [
                "Published taxes are not a minimum bid, total acquisition cost, "
                "or verified lien balance.",
                "Inspect the original catalog and sale terms for redemption, environmental "
                "and use restrictions.",
            ]
        )
        if len(description) > 6000:
            item.risk_notes.append(
                "Legal description is abbreviated here; read the full source catalog."
            )
        result.append(item)
    return checked(result)


def parse_treasury(html: str) -> list[PropertyRecord]:
    soup = BeautifulSoup(html, "html.parser")
    if "ONLINE AUCTION" not in text(soup):
        raise SourceUnavailable("Treasury inventory layout changed or empty")
    result: list[PropertyRecord] = []
    recognized = 0
    # Each sale occupies one text table cell; adjacent photo cells are not listings.
    for cell in soup.find_all("td"):
        value = text(cell)
        if "ONLINE AUCTION" not in value or cell.find("td"):
            continue
        recognized += 1
        if re.search(r"\b(?:CANCELLED|CANCELED|POSTPONED)\b", value, re.I):
            continue
        match = required_match(r"Sale\s*#\s*(\d{2}-\d{2}-\d{3,5})", value)
        identifier = match[1]
        heading, remainder = re.split(r"ONLINE AUCTION\s*DAT\s*E\s*:", value, maxsplit=1)
        state = next(
            (
                code
                for code, name in STATES.items()
                if re.search(rf",\s*{re.escape(name)}\s+\d{{5}}", heading, re.I)
            ),
            None,
        )
        if state is None:
            if ", Puerto Rico " in heading:
                continue  # This beta's geographic contract is the 50 states.
            raise SourceUnavailable("Treasury address has an unknown state")
        day = re.search(r"[A-Z][a-z]+ \d{1,2}, \d{4}", remainder)
        auction_date = datetime.strptime(day[0], "%B %d, %Y").date() if day else None
        if auction_date is None and "COMING SOON" not in remainder:
            raise SourceUnavailable("Treasury auction date is not recognized")
        anchor = next((a for a in cell.select("a[href]") if "complete details" in text(a)), None)
        url = urljoin(TREASURY, str(anchor["href"])) if anchor else TREASURY + "realprop.shtml"
        if not approved_url("us_treasury", url):
            raise SourceUnavailable("Treasury listing URL changed")
        acreage = re.search(r"([\d,.]+)\s*±?\s*acres", remainder)
        result.append(
            record(
                "us_treasury",
                id="treasury-" + identifier,
                tract=identifier,
                title=heading.strip()[:300],
                state=state,
                source_url=url,
                category="public_auction",
                sale_type="Federal forfeiture auction",
                sale_status="Auction scheduled" if auction_date else "Date not announced",
                auction_date=auction_date,
                acres=number(acreage[1]) if acreage else None,
                location_description=heading.split(":", 1)[-1].strip(),
            )
        )
    if not recognized:
        raise SourceUnavailable("Treasury inventory yielded no recognized sales")
    return checked(result)


def parse_alaska(html: str, program_html: str) -> list[PropertyRecord]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("section.js-parcel-card")
    if not cards:
        raise SourceUnavailable("Alaska inventory layout changed or empty")
    program = BeautifulSoup(program_html, "html.parser")
    dates: dict[str, tuple[date, date]] = {}
    for paragraph in program.find_all("p"):
        value = text(paragraph)
        m = re.search(
            r"Auction #(\d+).*?between [A-Za-z]+ \d+ and ([A-Za-z]+ \d+, \d{4})"
            r".*?held on ([A-Za-z]+ \d+, \d{4})",
            value,
        )
        if m:
            dates[m[1]] = (
                datetime.strptime(m[2], "%B %d, %Y").date(),
                datetime.strptime(m[3], "%B %d, %Y").date(),
            )
    result: list[PropertyRecord] = []
    for card in cards:
        offering, parcel = str(card.get("data-auction", "")), str(card.get("data-parcel", ""))
        identifier = offering + "-" + parcel
        if not re.fullmatch(r"\d{1,8}-\d{1,8}", identifier):
            raise SourceUnavailable("Invalid Alaska parcel identifier")
        price_label = text(card.select_one(".badge-price"))
        is_auction = str(card.get("data-program", "")).startswith("AUC-")
        if is_auction and offering not in dates:
            raise SourceUnavailable("Alaska auction bid deadline could not be confirmed")
        if not is_auction and "Price" not in price_label:
            raise SourceUnavailable("Unrecognized Alaska offering")
        img = card.select_one("img[data-src]")
        image = str(img["data-src"]) if img else None
        if image and not image.startswith(ALASKA + "/mlw/cdn/img/landsales/"):
            image = None
        deadline, auction = dates.get(offering, (None, None))
        result.append(
            record(
                "ak_dnr",
                id="ak-dnr-" + identifier,
                tract=identifier,
                title=f"{card.get('data-subd', 'State land')} · Parcel {identifier}"[:300],
                state="AK",
                source_url=ALASKA + "/mlw/landsales/parcels/details/" + identifier,
                acres=number(str(card.get("data-acres", ""))),
                asking_price=number(str(card.get("data-price", ""))),
                price_kind="Minimum bid" if is_auction else "Published sale price",
                category="government_land",
                sale_type="DNR land auction" if is_auction else "DNR direct sale",
                sale_status="Auction scheduled" if is_auction else "Available",
                image_url=image,
                bidding_deadline=deadline,
                auction_date=auction,
                location_description=f"{card.get('data-subd')} · {card.get('data-region')} region",
                eligibility="Alaska residents only"
                if card.get("data-resident-requirement") == "yes"
                else "Check source eligibility and offering terms",
            )
        )
    return checked(result)


def parse_michigan(html: str) -> list[PropertyRecord]:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("#ListView")
    if container is None:
        raise SourceUnavailable("Michigan inventory layout changed")
    cards = container.select(".card")
    if not cards and "No " not in text(soup):
        raise SourceUnavailable("Unexpected empty Michigan inventory")
    records: list[PropertyRecord] = []
    for card in cards:
        fields = {
            text(dt).rstrip(":"): text(dt.find_next_sibling("dd")) for dt in card.select("dt")
        }
        status = fields.get("Parcel Status")
        if status in {"Pending Bid Opening", "Pending Sale", "Sold", "Withdrawn"}:
            continue
        if status != "Available":
            raise SourceUnavailable("Unrecognized Michigan sale status")
        anchor = card.select_one('a[href*="/Parcels/Details?ParcelId="]')
        if anchor is None:
            raise SourceUnavailable("Michigan property link missing")
        identifier = required_match(
            r"^/LandSale/Parcels/Details\?ParcelId=(\d+)$", str(anchor["href"])
        )[1]
        parcel = required_match(r"^(\S+)\s+([^,]+),", fields.get("Parcel Number", ""))
        records.append(
            record(
                "mi_dnr",
                id="mi-dnr-" + identifier,
                tract=parcel[1],
                title="Parcel " + parcel[1],
                state="MI",
                county=parcel[2],
                source_url=MICHIGAN + str(anchor["href"]),
                acres=number(required_match(r"^([\d.,]+) acres$", fields.get("Size", ""))[1]),
                asking_price=number(fields.get("Minimum Accepted", "")),
                price_kind="Minimum bid",
                category="government_land",
                sale_type="DNR BuyNow surplus land",
                legal_description=fields.get("Description"),
                location_description=fields.get("Parcel Number"),
            )
        )
    return checked(records)


def parse_irs(html: str) -> tuple[list[PropertyRecord], bool]:
    soup = BeautifulSoup(html, "html.parser")
    if soup.select_one("#views-exposed-form-auction-items-block-1") is None:
        raise SourceUnavailable("IRS inventory layout changed")
    for name, expected in (("field_asset_type_target_id", "8"), ("field_sale_type_target_id", "1")):
        option = soup.select_one(f'select[name="{name}"] option[selected]')
        if option is None or option.get("value") != expected:
            raise SourceUnavailable("IRS did not apply the real-estate tax-seizure filters")
    result: list[PropertyRecord] = []
    for card in soup.select("article.irs-ad"):
        anchor = card.select_one("h3 a[href]")
        address = text(card.select_one("address"))
        state = required_match(r"\b([A-Z]{2}),?\s+\d{5}(?:-\d{4})?\b", address)[1].upper()
        identifier = required_match(r"^node-(\d{1,12})$", str(card.get("id", "")))[1]
        if anchor is None:
            raise SourceUnavailable("IRS property link missing")
        url = urljoin(IRS, str(anchor["href"]))
        if not approved_url("irs_auctions", url):
            raise SourceUnavailable("IRS property link is outside the reviewed source")
        when = card.select_one(".usa-card__body time")
        day = required_match(r"[A-Za-z]{3} \d{1,2}, \d{4}", text(when))[0]
        price = card.select_one(".field--name-field-minimum-bid .field__item")
        title = text(anchor)
        if re.search(r"cancel[le]*d|postponed", title, re.I):
            continue
        result.append(
            record(
                "irs_auctions",
                id="irs-" + identifier,
                tract=identifier,
                title=title[:300],
                state=state,
                source_url=url,
                category="tax_sale",
                sale_type="Federal tax-seizure auction",
                sale_status="Auction scheduled",
                auction_date=datetime.strptime(day, "%b %d, %Y").date(),
                asking_price=number(text(price)) if price else None,
                price_kind="Minimum bid",
                location_description=address,
            )
        )
    has_next = any(text(a).strip() == "Next" for a in soup.select("a[href]"))
    if (
        not soup.select("article.irs-ad")
        and "There are no" not in text(soup)
        and "No auctions" not in text(soup)
    ):
        raise SourceUnavailable("IRS inventory returned no recognized real estate")
    return checked(result), has_next


def usda_states(html: str) -> list[str]:
    return list(usda_state_counts(html))


def usda_state_counts(html: str) -> dict[str, int]:
    soup = BeautifulSoup(html, "html.parser")
    control = soup.select_one("#stateCode")
    if control is None:
        raise SourceUnavailable("USDA state coverage control missing")
    counts: dict[str, int] = {}
    for option in control.select("option[value]"):
        code = str(option["value"])
        if not code:
            continue
        count = int(required_match(r"\((\d+)\)$", text(option))[1])
        if not re.fullmatch(r"\d{2}", code) or code in counts or count > MAX_INVENTORY:
            raise SourceUnavailable("USDA advertised state inventory size invalid")
        counts[code] = count
    return counts


def parse_usda(html: str, kind: str) -> list[PropertyRecord]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("#propertySummariesTable")
    if table is None:
        raise SourceUnavailable("USDA search result table missing")
    headings = [text(th) for th in table.select("thead th")]
    price_heading = "Value/Bid" if kind == "FSA" else "Price/Bid"
    if not {"Listing Type", "Street Address", "State", "County", price_heading} <= set(headings):
        raise SourceUnavailable("USDA result headings changed")
    result: list[PropertyRecord] = []
    for row in table.select("tbody tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) != len(headings):
            raise SourceUnavailable("USDA result columns changed")
        fields = dict(zip(headings, cells, strict=True))
        anchor = row.select_one('a[href*="PropertyDetail?"]')
        if anchor is None:
            raise SourceUnavailable("USDA property link missing")
        url = urljoin(USDA, str(anchor["href"]))
        if not approved_url("usda_resales", url):
            raise SourceUnavailable("USDA property link outside reviewed source")
        identifier = parse_qs(urlsplit(url).query)["id"][0]
        listing_type = text(fields.get("Listing Type"))
        if listing_type not in {"Foreclosure", "REO Property"}:
            raise SourceUnavailable("Unknown USDA listing type")
        state_name = text(fields.get("State"))
        state = next((c for c, name in STATES.items() if state_name in {c, name}), None)
        if state is None:
            raise SourceUnavailable("USDA result state not recognized")
        street = fields.get("Street Address")
        if street is None:
            raise SourceUnavailable("USDA address missing")
        address = next(
            (str(v).strip() for v in street.contents if isinstance(v, str) and str(v).strip()), ""
        )
        price = text(fields.get(price_heading))
        if kind == "FSA" and listing_type == "REO Property":
            price = ""  # FSA's value column can be an appraisal, not an asking price.
        result.append(
            record(
                "usda_resales",
                id=f"usda-{kind.lower()}-{identifier}",
                tract=identifier,
                title=address or "USDA property " + identifier,
                state=state,
                county=text(fields.get("County")) or None,
                source_url=url,
                category="foreclosure",
                sale_type="USDA foreclosure"
                if listing_type == "Foreclosure"
                else "USDA bank-owned / REO sale",
                sale_status="Date not announced" if listing_type == "Foreclosure" else "Available",
                asking_price=number(price)
                if price and price not in {"N/A", "$0", "$0.00"}
                else None,
                price_kind="Government bid"
                if listing_type == "Foreclosure"
                else "Published sale price",
                location_description=(
                    f"{address}, {text(fields.get('City'))}, {state} {text(fields.get('Zip'))}"
                ),
            )
        )
    return checked(result)


def parse_usda_detail(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    if "Property Detail" not in text(soup):
        raise SourceUnavailable("USDA property detail layout changed")
    fields: dict[str, str] = {}
    for label in soup.select("div.col-md-4"):
        if text(label).endswith(":"):
            fields[text(label).rstrip(":")] = text(label.find_next_sibling("div"))
    result: dict[str, Any] = {"detail_retrieved_at": stamp()}
    appraisal = fields.get("Appraised Value", "")
    if appraisal:
        result["source_appraised_value"] = number(appraisal)
    total_acres = fields.get("Total Acres", "")
    if total_acres and number(total_acres) > 0:
        result["acres"] = number(total_acres)
    published_date = fields.get("Sale Date", "")
    if published_date:
        result["auction_date_text"] = published_date[:80]
        for pattern in ("%m/%d/%Y", "%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m-%d-%Y", "%m-%d-%y"):
            try:
                result.update(
                    auction_date=datetime.strptime(published_date, pattern).date(),
                    sale_status="Auction scheduled",
                )
                break
            except ValueError:
                continue
        else:
            # Ambiguous source dates are retained for review, never offered as current sales.
            result.update(active=False, sale_status="Date needs review")
    lot = fields.get("Lot Size", "")
    acreage = re.fullmatch(r"([\d.,]+)\s*(?:acres?|ac)", lot, re.I)
    if acreage and number(acreage[1]) > 0:
        result["acres"] = number(acreage[1])
    return result


async def retrieve(source: str, reader: PublicReader) -> list[PropertyRecord]:
    if source == "mn_dot":
        by_bid = parse_minnesota(await reader.read(PAGES[0]), by_bid=True)
        immediate = parse_minnesota(await reader.read(PAGES[1]), by_bid=False)
        return checked([*by_bid, *immediate])
    if source == "ar_cosl":
        records: list[PropertyRecord] = []
        catalogs = arkansas_catalog(
            await reader.read(ARKANSAS + "/Home/Contents"), datetime.now(UTC).date()
        )
        for url, day in catalogs:
            records.extend(parse_arkansas(await reader.read(url), url, day))
            checked(records)
        return checked(records)
    if source == "us_treasury":
        return parse_treasury(await reader.read(TREASURY + "realprop.shtml"))
    if source == "ak_dnr":
        program = await reader.read(ALASKA + "/mlw/landsales/")
        return parse_alaska(await reader.read(ALASKA + "/mlw/landsales/parcels"), program)
    if source == "mi_dnr":
        return parse_michigan(await reader.read(MICHIGAN + "/LandSale/Parcels/PublicSearch", {}))
    if source == "irs_auctions":
        records = []
        for page in range(50):
            url = (
                IRS
                + "/auction/items?"
                + urlencode(
                    {
                        "field_asset_type_target_id": "8",
                        "field_sale_type_target_id": "1",
                        "page": page,
                    }
                )
            )
            rows, more = parse_irs(await reader.read(url))
            records.extend(rows)
            checked(records)
            if not more:
                return checked(records)
        raise SourceUnavailable("IRS pagination exceeded reviewed limit")
    if source == "usda_resales":
        records = []
        for kind, property_type in (
            ("SFH", "Single Family"),
            ("MFH", "Multi-Family"),
            ("FSA", "Farm & Ranch"),
        ):
            url = USDA + "/resales/public/search" + kind
            for state, expected_count in usda_state_counts(await reader.read(url)).items():
                if not re.fullmatch(r"\d{2}", state):
                    raise SourceUnavailable("Invalid USDA state identifier")
                if state in {"60", "66", "69", "72", "78"}:
                    continue
                data = {
                    "stateCode": state,
                    "countyCode": "",
                    "city": "",
                    "zipCode": "",
                    "propertyType": property_type,
                    "listingType": "All Types",
                    "minPrice": "",
                    "maxPrice": "",
                    "bedrooms": "",
                    "bathrooms": "",
                    "squareFootage": "",
                    "searchFormName": kind,
                    "Search": "Search",
                }
                rows = parse_usda(await reader.read(url, data), kind)
                if len(rows) != expected_count:
                    raise SourceUnavailable("USDA inventory count changed during retrieval")
                for item in rows:
                    detail = parse_usda_detail(await reader.read(item.source_url))
                    records.append(PropertyRecord.model_validate({**item.model_dump(), **detail}))
                checked(records)
        return checked(records)
    raise SourceUnavailable("Source adapter is not registered")
