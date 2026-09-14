"""Explicit schema bootstrap and read-only source refresh commands."""

import argparse
import asyncio
import json

from landwolf.catalog import Catalog
from landwolf.config import Settings
from landwolf.db import database, initialize
from landwolf.research import ResearchQuery, ResearchService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init-db", "sync", "check-research"])
    parser.add_argument("--latitude", type=float, default=32.7767)
    parser.add_argument("--longitude", type=float, default=-96.7970)
    args = parser.parse_args()
    settings = Settings()
    engine, factory = database(settings.database_url)
    try:
        if args.command == "check-research":
            report = asyncio.run(
                ResearchService().lookup(
                    ResearchQuery(latitude=args.latitude, longitude=args.longitude)
                )
            )
            print(report.model_dump_json(indent=2))
            if report.status != "ready":
                raise SystemExit(1)
        elif args.command == "init-db":
            initialize(engine)
            print("Beta schema version 1 initialized; legacy tables unchanged")
        else:
            result = asyncio.run(Catalog(factory).refresh())
            print(json.dumps(result, indent=2))
            if any(source["automated"] and source["status"] != "ready" for source in result):
                raise SystemExit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
