"""Explicit, read-only upstream verification. Does not access any LandWolf database."""

import argparse
import asyncio
import json
from pathlib import Path

import httpx

from landwolf.commercial import PAGE_GROUPS, retrieve
from landwolf.config import Settings
from landwolf.provider import SourceUnavailable


async def check(sample_regions: bool, output: Path) -> int:
    sources = Settings().licensed_listing_sources
    if not sources:
        print("Not run: no provider agreements configured; no publisher requests made.")
        return 2
    results = []
    # Two independent state checks; each state's requests remain sequential and paced.
    slots = asyncio.Semaphore(2)
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(20, connect=8),
        follow_redirects=False,
        headers={"User-Agent": "LandWolf/0.17.0 (+https://github.com/lupu-spec/Landwolf)"},
    ) as client:

        async def one(source: str) -> None:
            async with slots:
                try:
                    async with asyncio.timeout(300):
                        rows = await retrieve(source, client, sample_regions=sample_regions)
                    result = {
                        "source": source,
                        "status": "passed",
                        "records": len(rows),
                        "regions_checked": 1 if sample_regions else len(PAGE_GROUPS[source]),
                        "with_price": sum(r.asking_price is not None for r in rows),
                        "with_acres": sum(r.acres is not None for r in rows),
                        "with_coordinates": sum(r.latitude is not None for r in rows),
                    }
                except (SourceUnavailable, httpx.HTTPError, ValueError, TimeoutError) as exc:
                    result = {
                        "source": source,
                        "status": "failed",
                        "error": type(exc).__name__,
                        "reason": str(exc)[:180],
                    }
                results.append(result)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(results, indent=2))
                print(json.dumps(result), flush=True)

        await asyncio.gather(*(one(source) for source in sources))
    return int(any(r["status"] != "passed" for r in results))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-regions", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("test-results/commercial-live.json"))
    args = parser.parse_args()
    raise SystemExit(asyncio.run(check(args.sample_regions, args.output)))


if __name__ == "__main__":
    main()
