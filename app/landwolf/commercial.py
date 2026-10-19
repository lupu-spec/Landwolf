"""Bounded public listing-page adapters. No private APIs, images or contact imports."""

import asyncio
import hashlib
import json
import re
from typing import Any
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from landwolf.craigslist_regions import REGIONS
from landwolf.provider import SourceUnavailable, stamp
from landwolf.schemas import PropertyRecord

PAGE_GROUPS = {
    "zillow_tx": ("https://www.zillow.com/tx/land/",),
    "compass_tx": ("https://www.compass.com/homes-for-sale/texas/land/",),
    **{
        f"craigslist_{state.lower()}": tuple(
            f"https://www.craigslist.org/search/area/{region}?cat=rea&query=land"
            for region in regions
        )
        for state, regions in REGIONS.items()
    },
}
PAGES = {source: pages[0] for source, pages in PAGE_GROUPS.items()}
NAMES = {
    source: "Craigslist"
    if source.startswith("craigslist_")
    else ("Zillow" if source == "zillow_tx" else "Compass")
    for source in PAGES
}
SCOPE = "Sampled listing page retrieved; partial coverage. Confirm details at the publisher."
MAX_BYTES = 8_000_000
MAX_ROWS = 500


def objects(documents: list[Any]) -> list[dict[str, Any]]:
    queue = list(documents)
    result: list[dict[str, Any]] = []
    for _ in range(50_000):
        if not queue:
            return result
        obj = queue.pop()
        if isinstance(obj, list):
            queue.extend(obj)
        elif isinstance(obj, dict):
            result.append(obj)
            queue.extend(obj.values())
    raise SourceUnavailable("Listing document exceeds structural limit")


def documents(soup: BeautifulSoup, kind: str) -> list[Any]:
    result = []
    for script in soup.find_all("script", attrs={"type": kind}):
        try:
            result.append(json.loads(script.get_text()))
        except (ValueError, RecursionError) as exc:
            raise SourceUnavailable("Invalid public listing JSON") from exc
    return result


def listing_url(source: str, value: str) -> str:
    url = urljoin(PAGES[source], value)
    p = urlsplit(url)
    host = urlsplit(PAGES[source]).hostname
    patterns = {
        "zillow_tx": r"/homedetails/[A-Za-z0-9_%-]+/[0-9]+_zpid/?",
        "craigslist": r"/view/d/[A-Za-z0-9_%-]+/[A-Za-z0-9_-]{8,60}",
        "compass_tx": r"/homedetails/[A-Za-z0-9_%-]+/[A-Za-z0-9_-]+_pid/?",
    }
    if (
        p.scheme != "https"
        or p.hostname != host
        or p.username
        or p.password
        or p.port
        or p.query
        or p.fragment
        or not re.fullmatch(
            patterns["craigslist" if source.startswith("craigslist_") else source], p.path
        )
    ):
        raise SourceUnavailable("Listing URL does not match publisher contract")
    return url


def value(number: Any) -> float | None:
    if number is None:
        return None
    if isinstance(number, bool):
        raise SourceUnavailable("Boolean is not a listing number")
    try:
        result = float(number)
    except (TypeError, ValueError) as exc:
        raise SourceUnavailable("Invalid listing number") from exc
    if not 0 <= result <= 1_000_000_000:
        raise SourceUnavailable("Listing number outside supported range")
    return result or None


def mapping(data: Any) -> dict[str, Any]:
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise SourceUnavailable("Invalid publisher object")
    return data


def coordinates(data: dict[str, Any]) -> dict[str, float | None]:
    try:
        lat, lon = data.get("latitude"), data.get("longitude")
        if lat is None and lon is None:
            return {"latitude": None, "longitude": None}
        if lat is None or lon is None or isinstance(lat, bool) or isinstance(lon, bool):
            raise ValueError
        lat, lon = float(lat), float(lon)
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError
        return {"latitude": lat, "longitude": lon}
    except (TypeError, ValueError) as exc:
        raise SourceUnavailable("Invalid published coordinate pair") from exc


def record(source: str, url: str, title: str, **fields: Any) -> PropertyRecord:
    if not title.strip():
        raise SourceUnavailable("Listing title missing")
    identity = hashlib.sha256(url.encode()).hexdigest()[:24]
    return PropertyRecord(
        id=f"{source}-{identity}",
        source=source,
        source_name=NAMES[source],
        source_url=listing_url(source, url),
        tract=identity,
        title=title,
        state=source.removeprefix("craigslist_").upper()
        if source.startswith("craigslist_")
        else "TX",
        category="seller_listing",
        sale_type="Seller / broker listing",
        sale_status="Publisher listing — verify availability",
        eligibility="Publisher listing; owner/broker identity and vacant-land status are not "
        "independently verified. Coverage is a sampled page, not the full market.",
        retrieved_at=stamp(),
        image_url=None,
        **fields,
    )


def zillow(soup: BeautifulSoup) -> list[PropertyRecord]:
    result = {}
    for obj in objects(documents(soup, "application/json")):
        if not obj.get("zpid") or not obj.get("detailUrl"):
            continue
        info = mapping(mapping(obj.get("hdpData")).get("homeInfo"))
        if info.get("state") != "TX" or info.get("homeType") not in {"LOT", "LAND"}:
            continue
        if info.get("homeStatus") != "FOR_SALE":
            continue
        size = value(info.get("lotAreaValue"))
        unit = str(info.get("lotAreaUnit", "")).lower()
        acres = (
            size
            if unit in {"acre", "acres"}
            else (
                size / 43560
                if size is not None and unit in {"sqft", "sq ft", "square feet"}
                else None
            )
        )
        item = record(
            "zillow_tx",
            obj["detailUrl"],
            str(obj.get("address") or ""),
            asking_price=value(obj.get("unformattedPrice")),
            acres=acres,
            acreage_basis="calculated" if acres and unit not in {"acre", "acres"} else "reported",
            location_description=str(obj.get("address") or ""),
            **coordinates(mapping(obj.get("latLong"))),
        )
        result[item.id] = item
    return list(result.values())


def craigslist(soup: BeautifulSoup, source: str) -> list[PropertyRecord]:
    places: dict[str, list[dict[str, Any]]] = {}
    for obj in objects(documents(soup, "application/ld+json")):
        if obj.get("@type") == "ListItem" and isinstance(obj.get("item"), dict):
            place = obj["item"]
            places.setdefault(" ".join(str(place.get("name", "")).split()), []).append(place)
    result = []
    cards = soup.select("li.cl-static-search-result")
    if len(cards) > MAX_ROWS:
        raise SourceUnavailable("Listing card limit exceeded")
    for card in cards:
        title = " ".join(str(card.get("title", "")).split())
        matches = places.get(title, [])
        if len(matches) != 1:
            continue
        place = matches[0]
        address = mapping(place.get("address"))
        if address.get("addressRegion") != source.removeprefix("craigslist_").upper():
            continue
        # Keyword searches contain houses, financing promotions and unrelated ads.
        if not re.search(r"\b(?:land|lot|acres?|ranch)\b", title, re.I) or re.search(
            r"\b(?:house|homes?|bedrooms?|bath|apartment|condo|rent|lease|monthly|down)\b",
            title,
            re.I,
        ):
            continue
        link, price = card.find("a", href=True), card.select_one(".price")
        if link is None:
            continue
        price_text = price.get_text(strip=True) if price else ""
        price_match = re.fullmatch(r"\$([0-9,]+)", price_text)
        acreage = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:acres?|ac\b)", title, re.I)
        result.append(
            record(
                source,
                str(link["href"]),
                title,
                asking_price=value(price_match[1].replace(",", "")) if price_match else None,
                acres=value(acreage[1]) if acreage else None,
                location_description=str(
                    address.get("addressLocality") or source.removeprefix("craigslist_").upper()
                ),
                **coordinates(place),
            )
        )
    return result


def compass(soup: BeautifulSoup) -> list[PropertyRecord]:
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    if not re.search(r"Land for Sale in Texas", title, re.I):
        raise SourceUnavailable("Compass land-search filter not confirmed")
    nodes = objects(documents(soup, "application/ld+json"))
    locations = {
        obj["url"]: obj
        for obj in nodes
        if isinstance(obj.get("url"), str)
        and isinstance(obj.get("address"), dict)
        and obj["address"].get("addressRegion") == "TX"
    }
    result = []
    for obj in nodes:
        if obj.get("@type") != "Product" or obj.get("url") not in locations:
            continue
        offer = mapping(obj.get("offers"))
        if (
            offer.get("priceCurrency") != "USD"
            or offer.get("availability") != "https://schema.org/InStock"
        ):
            continue
        location = locations[obj["url"]]
        address = location["address"]
        result.append(
            record(
                "compass_tx",
                obj["url"],
                str(obj.get("name") or address.get("streetAddress") or ""),
                asking_price=value(offer.get("price")),
                location_description=", ".join(
                    str(address.get(k) or "")
                    for k in ("streetAddress", "addressLocality", "addressRegion", "postalCode")
                ),
                **coordinates(mapping(location.get("geo"))),
            )
        )
    return result


def parse(source: str, html: str, *, allow_empty: bool = False) -> list[PropertyRecord]:
    if source not in PAGES or len(html.encode()) > MAX_BYTES:
        raise SourceUnavailable("Unsupported source or oversized page")
    soup = BeautifulSoup(html, "html.parser")
    try:
        if source.startswith("craigslist_"):
            if not soup.select("li.cl-static-search-result") and not any(
                obj.get("@type") == "ItemList"
                for obj in objects(documents(soup, "application/ld+json"))
            ):
                raise SourceUnavailable("Craigslist result structure not confirmed")
            rows = craigslist(soup, source)
        else:
            rows = (zillow if source == "zillow_tx" else compass)(soup)
    except (TypeError, AttributeError, KeyError) as exc:
        raise SourceUnavailable("Publisher listing structure changed; snapshot retained") from exc
    if (
        (not rows and not allow_empty)
        or len(rows) > MAX_ROWS
        or len({r.id for r in rows}) != len(rows)
    ):
        raise SourceUnavailable(
            "No supported listings or duplicate/oversized result; snapshot retained"
        )
    return rows


async def retrieve(
    source: str, client: httpx.AsyncClient, *, sample_regions: bool = False
) -> list[PropertyRecord]:
    pages = PAGE_GROUPS[source]
    if sample_regions:
        pages = pages[:1]
    page = pages[0]
    origin = "https://" + str(urlsplit(page).hostname)

    async def read(url: str, *, robots: bool = False) -> str:
        if url not in {*pages, origin + "/robots.txt"}:
            raise SourceUnavailable("Unapproved commercial source request")
        async with client.stream("GET", url) as response:
            if robots and response.status_code == 404:
                return ""
            if response.status_code != 200:
                raise SourceUnavailable(
                    f"Publisher returned HTTP {response.status_code}; no bypass"
                )
            content_type = response.headers.get("content-type", "").lower()
            if (robots and "text/plain" not in content_type) or (
                not robots and "text/html" not in content_type
            ):
                raise SourceUnavailable("Unexpected publisher content type")
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > (200_000 if robots else MAX_BYTES):
                    raise SourceUnavailable("Publisher response exceeds size limit")
        return body.decode("utf-8")

    policy = RobotFileParser()
    policy.parse((await read(origin + "/robots.txt", robots=True)).splitlines())
    agent = client.headers.get("user-agent", "LandWolf")
    delay = int(policy.crawl_delay(agent) or 0)
    if any(not policy.can_fetch(agent, page) for page in pages) or delay > 10:
        raise SourceUnavailable("Publisher crawl policy requires deferring this refresh")
    results: dict[str, PropertyRecord] = {}
    for index, page in enumerate(pages):
        if index or delay:
            await asyncio.sleep(max(1, delay))
        for item in parse(source, await read(page), allow_empty=source.startswith("craigslist_")):
            results[item.id] = item
        if len(results) > 5000:
            raise SourceUnavailable("State listing limit exceeded; snapshot retained")
    return list(results.values())
