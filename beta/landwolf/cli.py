"""Explicit schema bootstrap and read-only source refresh commands."""

import argparse
import asyncio
import json

from landwolf.catalog import Catalog
from landwolf.config import Settings
from landwolf.db import database, initialize


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init-db", "sync"])
    args = parser.parse_args()
    settings = Settings()
    engine, factory = database(settings.database_url)
    try:
        if args.command == "init-db":
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
