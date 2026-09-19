"""Synthetic public API responses; only tests import this module."""

import json
import os
from pathlib import Path

import httpx
from fastapi import FastAPI

from landwolf.research import CENSUS, FEMA, NC, SOIL, SOIL_COLUMNS, USGS


def public_response(request: httpx.Request) -> httpx.Response:
    endpoint = str(request.url).split("?")[0]
    geography = {
        "States": [{"STUSAB": "NC"}],
        "Counties": [{"NAME": "Fixture County", "GEOID": "37999"}],
        "Census Tracts": [{"GEOID": "37999000100"}],
    }
    if endpoint == CENSUS + "coordinates":
        # The browser handoff fixture is a TX listing; preserve the real state
        # consistency check instead of returning the unrelated NC address fixture.
        if request.url.params.get("x") == "-98.5175":
            geography = {
                "States": [{"STUSAB": "TX"}],
                "Counties": [{"NAME": "Fixture Eastland", "GEOID": "48999"}],
                "Census Tracts": [{"GEOID": "48999000100"}],
            }
        data = {"result": {"geographies": geography}}
    elif endpoint == CENSUS + "onelineaddress":
        data = {
            "result": {
                "addressMatches": [
                    {
                        "matchedAddress": "1 SYNTHETIC WAY, FIXTURE, NC 27000",
                        "coordinates": {"x": -78.6391, "y": 35.7804},
                        "geographies": geography,
                    }
                ]
            }
        }
    elif endpoint == FEMA + "0/query":
        data = {"features": [{"attributes": {"STUDY_ID": "37999"}}]}
    elif endpoint == FEMA + "28/query":
        data = {
            "features": [
                {
                    "attributes": {
                        "FLD_ZONE": "X",
                        "SFHA_TF": "F",
                        "DFIRM_ID": "37999",
                        "ZONE_SUBTY": "Synthetic test zone",
                        "SOURCE_CIT": "Fixture citation",
                    }
                }
            ]
        }
    elif endpoint == USGS:
        data = {"value": "0", "resolution": 1, "attributes": {"AcquisitionDate": "1/1/2020"}}
    elif endpoint == SOIL:
        data = {
            "Table": [
                SOIL_COLUMNS,
                [
                    "999",
                    "TEST",
                    "Synthetic soils",
                    "Not prime farmland",
                    "Fixture component",
                    "100",
                    None,
                    "D",
                    "0",
                ],
            ]
        }
    elif endpoint == NC:
        data = {
            "features": [
                {
                    "attributes": {
                        "parno": "FIXTURE-999",
                        "nparno": "37999_FIXTURE",
                        "siteadd": "1 Synthetic Way",
                        "cntyname": "Fixture",
                        "stcntyfips": "37999",
                        "gisacres": 1.25,
                        "landval": 10000,
                        "improvval": 0,
                        "parval": None,
                        "parvaltype": "Assessed",
                        "sourceagnt": "Synthetic county assessor",
                        "transfdate": 1767225600000,
                        "revdatetx": "2025-12-01",
                        "ownname": "DO NOT RETAIN OWNER FIELD",
                    }
                }
            ]
        }
    else:
        raise AssertionError(f"Unexpected public endpoint: {endpoint}")
    return httpx.Response(200, json=data)


def create_fixture_app() -> FastAPI:
    from landwolf.main import create_app

    app = create_app()
    app.state.research.transport = httpx.MockTransport(public_response)
    mailbox = os.environ.get("LANDWOLF_TEST_MAILBOX")
    if mailbox:

        class FixtureMailer:
            enabled = True

            async def send(self, email: str, purpose: str, token: str) -> None:
                path = Path(mailbox)
                path.touch(mode=0o600, exist_ok=True)
                path.write_text(json.dumps({"purpose": purpose, "token": token}))

        app.state.mailer = FixtureMailer()
    return app
