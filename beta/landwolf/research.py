"""Free public location research. Never turns reference data into a sale or valuation."""

import asyncio
import hashlib
import json
import math
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, Literal, Self

import httpx
from pydantic import Field, model_validator

from landwolf.schemas import Contract
from landwolf.states import STATES

CENSUS = "https://geocoding.geo.census.gov/geocoder/geographies/"
FEMA = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/"
USGS = "https://epqs.nationalmap.gov/v1/json"
SOIL = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
NC = "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1/query"
ENDPOINTS = frozenset(
    [
        CENSUS + "coordinates",
        CENSUS + "onelineaddress",
        FEMA + "0/query",
        FEMA + "28/query",
        USGS,
        SOIL,
        NC,
    ]
)
MAX_BYTES = 2_000_000
MAX_RECORDS = 20
SOIL_COLUMNS = [
    "mukey",
    "musym",
    "muname",
    "farmlndcl",
    "compname",
    "comppct_r",
    "drainagecl",
    "hydgrp",
    "slope_r",
]
SOIL_QUERY = """SELECT TOP 21 m.mukey,m.musym,m.muname,m.farmlndcl,
c.compname,c.comppct_r,c.drainagecl,c.hydgrp,c.slope_r
FROM mapunit m LEFT JOIN component c ON c.mukey=m.mukey
WHERE m.mukey IN (SELECT * FROM
SDA_Get_Mukey_from_intersection_with_WktWgs84('POINT_LITERAL'))
ORDER BY m.mukey,c.comppct_r DESC,c.cokey"""
NC_FIELDS = (
    "parno,nparno,siteadd,scity,szip,cntyname,stcntyfips,gisacres,landval,improvval,"
    "parval,parvaltype,parusedesc,structyear,saledatetx,sourceagnt,transfdate,revdatetx"
)
RESEARCH_SOURCES = (
    {
        "id": "census",
        "name": "U.S. Census Geocoder",
        "url": "https://geocoding.geo.census.gov/geocoder/",
        "coverage": "All 50 states; address matching and geographic identifiers. "
        "Address points are interpolated, not parcel boundaries.",
    },
    {
        "id": "fema",
        "name": "FEMA National Flood Hazard Layer",
        "url": "https://www.fema.gov/flood-maps/national-flood-hazard-layer",
        "coverage": "Effective digital flood mapping where available. "
        "An empty response never establishes low flood risk.",
    },
    {
        "id": "usgs",
        "name": "USGS Elevation Point Query Service",
        "url": "https://epqs.nationalmap.gov/v1/docs",
        "coverage": "Ground elevation and source resolution at a point; "
        "coverage and acquisition dates vary.",
    },
    {
        "id": "soil",
        "name": "USDA NRCS Soil Data Access",
        "url": "https://sdmdataaccess.nrcs.usda.gov/",
        "coverage": "Mapped soil units, components, drainage and farmland classification "
        "where surveyed. Not a site soil or septic test.",
    },
    {
        "id": "nc_parcels",
        "name": "North Carolina OneMap parcels",
        "url": "https://www.nconemap.gov/pages/parcels",
        "coverage": "North Carolina county parcel identifiers, GIS acreage and reported tax "
        "values. County update dates vary; not a listing feed or market valuation.",
    },
)


class ResearchUnavailable(Exception):
    """A source contract or bounded request failed; never echo response bodies."""


class ResearchBusy(Exception):
    """The bounded shared work capacity is occupied."""


class ResearchQuery(Contract):
    address: str | None = Field(default=None, min_length=8, max_length=240)
    latitude: float | None = Field(default=None, ge=-90, le=90, strict=True)
    longitude: float | None = Field(default=None, ge=-180, le=180, strict=True)
    listing_id: str | None = Field(
        default=None, min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$"
    )

    @model_validator(mode="after")
    def one_location(self) -> Self:
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Supply both latitude and longitude")
        if (
            sum([self.address is not None, self.latitude is not None, self.listing_id is not None])
            != 1
        ):
            raise ValueError("Use an address, coordinates, or a listing, not a combination")
        if self.address is not None:
            if any(ord(c) < 32 for c in self.address) or len(self.address.strip()) < 8:
                raise ValueError("Supply a complete street address")
            self.address = self.address.strip()
        return self


class ResearchPoint(Contract):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    label: str = Field(max_length=300)
    basis: Literal[
        "Census address approximation", "User-supplied coordinate", "Source-published coordinate"
    ]
    state: str = ""


class Fact(Contract):
    label: str = Field(max_length=100)
    value: str = Field(max_length=800)


class ResearchSection(Contract):
    title: str = Field(max_length=300)
    facts: list[Fact] = Field(default_factory=list, max_length=25)


class ResearchSource(Contract):
    id: str
    name: str
    url: str
    status: Literal["ready", "unavailable", "no_data", "not_applicable"]
    retrieved_at: str
    summary: str
    limitation: str
    sections: list[ResearchSection] = Field(default_factory=list, max_length=MAX_RECORDS)


class ResearchReport(Contract):
    status: Literal["ready", "partial", "no_match", "ambiguous", "unavailable", "outside_coverage"]
    message: str
    location: ResearchPoint | None = None
    sources: list[ResearchSource] = Field(default_factory=list, max_length=5)
    cached: bool = False


def stamp() -> str:
    return datetime.now(UTC).isoformat()


def clean(value: Any) -> str:
    if value is None or value == "":
        return "Not published"
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise ResearchUnavailable("Invalid source field")
    if isinstance(value, float) and not math.isfinite(value):
        raise ResearchUnavailable("Non-finite source field")
    text = " ".join(str(value).split())
    if len(text) > 800:
        raise ResearchUnavailable("Source text too long")
    return text


def numeric(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ResearchUnavailable("Invalid number")
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ResearchUnavailable("Invalid source number") from exc
    if not math.isfinite(number):
        raise ResearchUnavailable("Non-finite source number")
    return None if number in {-9999, -999999, -1000000} else number


def amount(value: Any, *, unit: str = "", maximum: float = 100_000_000_000) -> str:
    number = numeric(value)
    if number is None:
        return "Not published"
    if number < 0 or number > maximum:
        raise ResearchUnavailable("Source number out of range")
    return f"{number:,.4f}".rstrip("0").rstrip(".") + unit


def section(title: str, **values: Any) -> ResearchSection:
    return ResearchSection(
        title=title, facts=[Fact(label=k, value=clean(v)) for k, v in values.items()]
    )


def source_result(
    source_id: str,
    status: Literal["ready", "unavailable", "no_data", "not_applicable"],
    summary: str,
    sections: list[ResearchSection] | None = None,
) -> ResearchSource:
    spec = next(s for s in RESEARCH_SOURCES if s["id"] == source_id)
    return ResearchSource(
        id=source_id,
        name=spec["name"],
        url=spec["url"],
        status=status,
        retrieved_at=stamp(),
        summary=summary,
        limitation=spec["coverage"],
        sections=sections or [],
    )


def features(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = data.get("features")
    if not isinstance(rows, list) or len(rows) > MAX_RECORDS or data.get("exceededTransferLimit"):
        raise ResearchUnavailable("Incomplete geographic result")
    if any(
        not isinstance(row, dict) or not isinstance(row.get("attributes"), dict) for row in rows
    ):
        raise ResearchUnavailable("Invalid geographic result")
    return [row["attributes"] for row in rows]


def object_field(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ResearchUnavailable("Invalid source object")
    return value


def source_date(value: Any) -> str | None:
    timestamp = numeric(value)
    if timestamp is None:
        return None
    # Reject impossible dates before platform timestamp conversion.
    if not -2208988800000 <= timestamp <= 4102444800000:
        raise ResearchUnavailable("Invalid source timestamp")
    return datetime.fromtimestamp(timestamp / 1000, UTC).date().isoformat()


class JsonReader:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client
        self.requests = 0

    async def read(
        self, url: str, params: dict[str, str] | None = None, body: dict[str, str] | None = None
    ) -> dict[str, Any]:
        if url not in ENDPOINTS:
            raise ResearchUnavailable("Unapproved endpoint")
        for attempt in range(2):
            self.requests += 1
            if self.requests > 14:
                raise ResearchUnavailable("Request budget exhausted")
            try:
                async with self.client.stream(
                    "POST" if body else "GET", url, params=params, json=body
                ) as response:
                    response.raise_for_status()
                    if "application/json" not in response.headers.get("content-type", "").lower():
                        raise ResearchUnavailable("Expected JSON")
                    content = bytearray()
                    async for chunk in response.aiter_bytes():
                        content.extend(chunk)
                        if len(content) > MAX_BYTES:
                            raise ResearchUnavailable("Response too large")
                    result = json.loads(content)
                    if not isinstance(result, dict) or "error" in result or "errors" in result:
                        raise ResearchUnavailable("Invalid source response")
                    return result
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt:
                    raise
            except httpx.HTTPStatusError as exc:
                if attempt or exc.response.status_code not in {429, 502, 503, 504}:
                    raise
            await asyncio.sleep(0.25)
        raise ResearchUnavailable("Source unavailable")


async def census(
    reader: JsonReader, query: ResearchQuery, point: ResearchPoint | None
) -> tuple[ResearchPoint | None, ResearchSource, str]:
    params = {
        "benchmark": "Public_AR_Current",
        "vintage": "Current_Current",
        "layers": "Counties,States,Census Tracts",
        "format": "json",
    }
    if query.address:
        params["address"] = query.address
        data = await reader.read(CENSUS + "onelineaddress", params)
        result = object_field(data.get("result"))
        matches = result.get("addressMatches")
        if not isinstance(matches, list):
            raise ResearchUnavailable("Invalid address response")
        if len(matches) != 1:
            status = "ambiguous" if matches else "no_match"
            return (
                None,
                source_result(
                    "census",
                    "no_data",
                    "Address was not uniquely matched. "
                    "Supply a full address or verified coordinates.",
                ),
                status,
            )
        match = object_field(matches[0])
        coordinates = object_field(match.get("coordinates"))
        point = ResearchPoint(
            latitude=coordinates["y"],
            longitude=coordinates["x"],
            label=match["matchedAddress"],
            basis="Census address approximation",
        )
        geographies = match.get("geographies")
    else:
        if point is None:
            raise ResearchUnavailable("Missing point")
        params.update(x=str(point.longitude), y=str(point.latitude))
        data = await reader.read(CENSUS + "coordinates", params)
        result = object_field(data.get("result"))
        geographies = result.get("geographies")
    if not isinstance(geographies, dict):
        raise ResearchUnavailable("Missing geography")
    states, counties, tracts = (
        geographies.get(k, []) for k in ("States", "Counties", "Census Tracts")
    )
    if any(
        not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows)
        for rows in (states, counties, tracts)
    ):
        raise ResearchUnavailable("Invalid geography records")
    if not states:
        return (
            None,
            source_result("census", "no_data", "No U.S. state was identified at this point."),
            "outside_coverage",
        )
    if len(states) != 1 or len(counties) > 1 or len(tracts) > 1:
        raise ResearchUnavailable("Ambiguous geography")
    state = states[0].get("STUSAB")
    if not isinstance(state, str):
        raise ResearchUnavailable("Invalid state identifier")
    if state not in STATES:
        return (
            None,
            source_result(
                "census",
                "not_applicable",
                "This research tool currently covers the 50 U.S. states.",
            ),
            "outside_coverage",
        )
    if point.state and point.state != state:
        raise ResearchUnavailable("Published point conflicts with listing state")
    point.state = state
    vintage = object_field(object_field(result.get("input", {})).get("vintage", {}))
    facts = {
        "State": STATES[state],
        "County": counties[0].get("NAME") if counties else None,
        "County GEOID": counties[0].get("GEOID") if counties else None,
        "Census tract GEOID": tracts[0].get("GEOID") if tracts else None,
        "Geography vintage": vintage.get("vintageName", "Current_Current"),
    }
    return (
        point,
        source_result(
            "census",
            "ready",
            "Geographic identifiers at the research point.",
            [section("Location context", **facts)],
        ),
        "ready",
    )


def spatial(point: ResearchPoint, fields: str) -> dict[str, str]:
    return {
        "f": "json",
        "geometry": f"{point.longitude},{point.latitude}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": fields,
        "returnGeometry": "false",
        "resultRecordCount": "21",
    }


async def flood(reader: JsonReader, point: ResearchPoint) -> ResearchSource:
    availability = features(await reader.read(FEMA + "0/query", spatial(point, "STUDY_ID")))
    if not availability:
        return source_result(
            "fema",
            "no_data",
            "No effective digital NFHL coverage was returned. Flood risk is unknown.",
        )
    zones = features(
        await reader.read(
            FEMA + "28/query", spatial(point, "FLD_ZONE,ZONE_SUBTY,SFHA_TF,DFIRM_ID,SOURCE_CIT")
        )
    )
    if not zones:
        return source_result(
            "fema",
            "no_data",
            "Digital coverage exists, but no flood-zone polygon was returned. "
            "Flood risk is unknown.",
        )
    sections = []
    for zone in zones:
        flag = zone.get("SFHA_TF")
        if flag not in {"T", "F", None, ""} or not zone.get("FLD_ZONE"):
            raise ResearchUnavailable("Invalid flood-zone attributes")
        sections.append(
            section(
                "Mapped flood zone",
                **{
                    "Zone": zone["FLD_ZONE"],
                    "Zone description": zone.get("ZONE_SUBTY"),
                    "Special Flood Hazard Area": {"T": "Yes", "F": "No"}.get(str(flag), "Unknown"),
                    "Study ID": zone.get("DFIRM_ID"),
                    "Source citation": zone.get("SOURCE_CIT"),
                },
            )
        )
    return source_result(
        "fema",
        "ready",
        "Point screening only. Confirm the full parcel and structures with FEMA "
        "and local floodplain officials; even Zone X can flood.",
        sections,
    )


async def elevation(reader: JsonReader, point: ResearchPoint) -> ResearchSource:
    data = await reader.read(
        USGS,
        {
            "x": str(point.longitude),
            "y": str(point.latitude),
            "units": "Meters",
            "wkid": "4326",
            "includeDate": "true",
        },
    )
    value = numeric(data.get("value"))
    if value is None:
        return source_result("usgs", "no_data", "No elevation value was returned.")
    if not -500 <= value <= 10000:
        raise ResearchUnavailable("Invalid elevation")
    return source_result(
        "usgs",
        "ready",
        "Ground elevation sampled from the USGS terrain model, not a surveyed building elevation.",
        [
            section(
                "Terrain",
                **{
                    "Elevation (meters)": f"{value:,.2f}",
                    "Elevation (feet)": f"{value / 0.3048:,.2f}",
                    "Source resolution (meters)": amount(data.get("resolution")),
                    "Acquisition date": object_field(data.get("attributes", {})).get(
                        "AcquisitionDate"
                    ),
                },
            )
        ],
    )


async def soils(reader: JsonReader, point: ResearchPoint) -> ResearchSource:
    # SDA accepts SQL, not bind parameters. Only validated finite numeric coordinates
    # enter this fixed read-only template; no user text or SQL is accepted.
    wkt = f"point ({point.longitude:.7f} {point.latitude:.7f})"
    data = await reader.read(
        SOIL, body={"query": SOIL_QUERY.replace("POINT_LITERAL", wkt), "format": "JSON+COLUMNNAME"}
    )
    table = data.get("Table")
    if table is None or table == []:
        return source_result(
            "soil", "no_data", "No mapped soil unit was returned. Soil conditions remain unknown."
        )
    if not isinstance(table, list) or table[0] != SOIL_COLUMNS or len(table) > MAX_RECORDS + 1:
        raise ResearchUnavailable("Invalid or incomplete soils table")
    sections = []
    for row in table[1:]:
        if not isinstance(row, list) or len(row) != len(SOIL_COLUMNS):
            raise ResearchUnavailable("Invalid soils row")
        values = dict(zip(SOIL_COLUMNS, row, strict=True))
        sections.append(
            section(
                clean(values["muname"]),
                **{
                    "Map unit key": values["mukey"],
                    "Map unit symbol": values["musym"],
                    "Farmland classification": values["farmlndcl"],
                    "Component": values["compname"],
                    "Component share (%)": amount(values["comppct_r"], maximum=100),
                    "Drainage class": values["drainagecl"],
                    "Hydrologic soil group": values["hydgrp"],
                    "Representative slope (%)": amount(values["slope_r"], maximum=1000),
                },
            )
        )
    return source_result(
        "soil",
        "ready" if sections else "no_data",
        "Soil Survey Staff, USDA NRCS. Components describe a mapped soil unit, "
        "not exact conditions everywhere on a parcel.",
        sections,
    )


async def parcels(reader: JsonReader, point: ResearchPoint) -> ResearchSource:
    if point.state != "NC":
        return source_result(
            "nc_parcels",
            "not_applicable",
            "Parcel attributes are connected for North Carolina only. "
            "Nationwide assessor and deed records are not connected.",
        )
    rows = features(await reader.read(NC, spatial(point, NC_FIELDS)))
    sections = []
    for row in rows:
        if not row.get("parno") or not str(row.get("stcntyfips", "")).startswith("37"):
            raise ResearchUnavailable("Invalid NC parcel")
        # Do not request, retain or display owner names or mailing/contact fields.
        sections.append(
            section(
                "Candidate parcel " + clean(row["parno"]),
                **{
                    "Parcel number": row["parno"],
                    "National parcel number": row.get("nparno"),
                    "Site address": row.get("siteadd"),
                    "County": row.get("cntyname"),
                    "GIS acres": amount(row.get("gisacres")),
                    "Reported parcel value (USD)": amount(row.get("parval")),
                    "Reported land value (USD)": amount(row.get("landval")),
                    "Reported improvement value (USD)": amount(row.get("improvval")),
                    "Type of value reported": row.get("parvaltype"),
                    "Tax parcel use": row.get("parusedesc"),
                    "Structure year": row.get("structyear") or None,
                    "Last sale date (source text)": row.get("saledatetx"),
                    "County data source": row.get("sourceagnt"),
                    "Record revised date (source text)": row.get("revdatetx"),
                    "Dataset transform date (UTC)": source_date(row.get("transfdate")),
                },
            )
        )
    return source_result(
        "nc_parcels",
        "ready" if sections else "no_data",
        "Point-intersecting candidate parcels from NCCGIA and NC county governments. "
        "Confirm parcel identity with the county; tax values are not market values "
        "or asking prices.",
        sections,
    )


class ResearchService:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.transport = transport
        self.cache: OrderedDict[str, tuple[float, ResearchReport]] = OrderedDict()
        self.active = 0

    async def lookup(
        self, query: ResearchQuery, point: ResearchPoint | None = None
    ) -> ResearchReport:
        if query.latitude is not None and query.longitude is not None:
            point = ResearchPoint(
                latitude=query.latitude,
                longitude=query.longitude,
                label="Supplied research point",
                basis="User-supplied coordinate",
            )
        key = hashlib.sha256(
            (query.model_dump_json() + (point.model_dump_json() if point else "")).encode()
        ).hexdigest()
        cached = self.cache.get(key)
        if cached and cached[0] > time.monotonic():
            self.cache.move_to_end(key)
            return cached[1].model_copy(deep=True, update={"cached": True})
        if self.active >= 4:
            raise ResearchBusy
        self.active += 1
        try:
            async with httpx.AsyncClient(
                transport=self.transport,
                timeout=httpx.Timeout(15, connect=5),
                follow_redirects=False,
                headers={
                    "User-Agent": "LandWolfBeta/0.2 (+https://github.com/lupu-spec/Landwolf)",
                    "Accept": "application/json",
                },
            ) as client:
                reader = JsonReader(client)
                try:
                    async with asyncio.timeout(25):
                        point, geography, state = await census(reader, query, point)
                except (
                    ResearchUnavailable,
                    httpx.HTTPError,
                    ValueError,
                    KeyError,
                    TypeError,
                    TimeoutError,
                ):
                    point, state = None, "unavailable"
                    geography = source_result(
                        "census",
                        "unavailable",
                        "Location lookup is temporarily unavailable. "
                        "No property facts were inferred.",
                    )
                if point is None:
                    report = ResearchReport(
                        status=state, message=geography.summary, sources=[geography]
                    )
                else:

                    async def one(
                        source_id: str,
                        fetch: Callable[[JsonReader, ResearchPoint], Awaitable[ResearchSource]],
                    ) -> ResearchSource:
                        try:
                            async with asyncio.timeout(30):
                                return await fetch(reader, point)
                        except (
                            ResearchUnavailable,
                            httpx.HTTPError,
                            ValueError,
                            KeyError,
                            TypeError,
                            TimeoutError,
                        ):
                            return source_result(
                                source_id,
                                "unavailable",
                                "This source did not return a complete valid response. "
                                "Its findings are unknown; other sources remain available.",
                            )

                    results = await asyncio.gather(
                        one("fema", flood),
                        one("usgs", elevation),
                        one("soil", soils),
                        one("nc_parcels", parcels),
                    )
                    report = ResearchReport(
                        status="partial"
                        if any(r.status in {"unavailable", "no_data"} for r in results)
                        else "ready",
                        message="Reference research at one point. Verify boundaries, title, "
                        "liens and site conditions separately. "
                        "These records do not establish a property is for sale.",
                        location=point,
                        sources=[geography, *results],
                    )
            ttl = 21600 if report.status == "ready" else 60
            self.cache[key] = (time.monotonic() + ttl, report.model_copy(deep=True))
            self.cache.move_to_end(key)
            while len(self.cache) > 128:
                self.cache.popitem(last=False)
            return report
        finally:
            self.active -= 1
