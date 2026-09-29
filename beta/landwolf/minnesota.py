"""MnDOT's published sale lists. Never infer PDF-only prices or parcel coordinates."""

import re
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup

from landwolf.provider import SourceUnavailable, stamp
from landwolf.schemas import PropertyRecord

BASE = "https://www.dot.state.mn.us/row/"
PAGES = (BASE + "propsales.html", BASE + "propsales_over_the_counter.html")


def parse_minnesota(html: str, *, by_bid: bool) -> list[PropertyRecord]:
    soup = BeautifulSoup(html, "html.parser")
    label = "Current properties for sale by bid" if by_bid else "Properties currently available"
    heading = next((h for h in soup.select("h3,h4") if h.get_text(" ", strip=True) == label), None)
    if heading is None:
        raise SourceUnavailable("Minnesota sale-list heading changed")
    listing = heading.find_next_sibling("ul")
    if listing is None:
        raise SourceUnavailable("Minnesota sale list missing")
    rows = listing.find_all("li", recursive=False)
    if not rows or len(rows) > 200:
        raise SourceUnavailable("Minnesota inventory size requires review")
    date_match = re.search(
        r"Last Update:\s*([A-Za-z]+ \d{1,2}, \d{4})", soup.get_text(" ", strip=True)
    )
    updated = datetime.strptime(date_match[1], "%B %d, %Y").date() if date_match else None
    result = []
    for row in rows:
        description = " ".join(row.get_text(" ", strip=True).split())
        link = row.find("a", href=True)
        if link is None:
            raise SourceUnavailable("Minnesota sale document missing")
        sale = re.fullmatch(r"Sale (\d{1,12})", link.get_text(strip=True))
        doc_url = str(link["href"])
        parts = urlsplit(doc_url)
        query = parse_qs(parts.query)
        if not (
            sale
            and parts.scheme == "https"
            and parts.netloc == "edocs-public.dot.state.mn.us"
            and parts.path == "/edocs_public/DMResultSet/download"
            and not parts.fragment
            and set(query) == {"docId"}
            and len(query["docId"]) == 1
            and re.fullmatch(r"\d{1,12}", query["docId"][0])
        ):
            raise SourceUnavailable("Minnesota sale identifier or document URL changed")
        size = re.search(
            r"([\d,.]+) (Acres|Square Feet) of (.+?) located (?:at|on|in) "
            r"(.+?), ([A-Za-z .'-]+) County, MN",
            description,
        )
        if size is None:
            raise SourceUnavailable("Minnesota property description changed")
        # Retain sale notices in the source; past or canceled events never enter active search.
        inactive = bool(re.search(r"\b(cancelled|canceled|withdrawn|sold)\b", description, re.I))
        auction = None
        if by_bid:
            day = re.search(r"Bid Opening ([A-Za-z]+ \d{1,2}, \d{4})", description)
            if day is None:
                raise SourceUnavailable("Minnesota bid-opening date missing")
            auction = datetime.strptime(day[1], "%B %d, %Y").date()
            inactive = inactive or auction < datetime.now(UTC).date()
        amount = float(size[1].replace(",", ""))
        acres = amount / 43560 if size[2] == "Square Feet" else amount
        record = PropertyRecord(
            id="mn-dot-" + sale[1],
            source="mn_dot",
            source_name="Minnesota Department of Transportation",
            source_url=doc_url,
            tract=sale[1],
            title=f"MnDOT sale {sale[1]}",
            state="MN",
            county=size[5],
            acres=acres,
            asking_price=None,
            category="surplus",
            acreage_basis="calculated" if size[2] == "Square Feet" else "reported",
            sale_type="Sealed-bid surplus property"
            if by_bid
            else "Immediate-purchase surplus property",
            sale_status="Auction scheduled" if by_bid else "Available",
            auction_date=auction,
            bidding_deadline=auction,
            active=not inactive,
            retrieved_at=stamp(),
            location_description=size[4],
            source_effective_date=updated,
            eligibility="Read the sale document for eligibility, deposits and purchase terms.",
        )
        record.risk_notes.extend(
            [
                "Price and parcel number require review of the sale document; neither is inferred.",
                "Publisher date refers to the inventory page, not verification of each parcel.",
            ]
        )
        if by_bid:
            record.risk_notes.append(
                "The listing page says bids must arrive by 1:45 PM at Central Office on the "
                "opening day. Confirm the time zone and instructions in the sale document."
            )
        if size[2] == "Square Feet":
            record.risk_notes.append(
                "Acreage calculated from published square feet using 43,560 square feet per acre."
            )
        result.append(record)
    if len({record.id for record in result}) != len(result):
        raise SourceUnavailable("Duplicate Minnesota sale numbers")
    return result
