"""Explicit schema bootstrap and read-only source refresh commands."""

import argparse
import asyncio
import json
import time

from sqlalchemy import select

from landwolf.catalog import Catalog
from landwolf.config import Settings
from landwolf.db import SCHEMA_VERSION, SourceRun, database, initialize
from landwolf.research import ResearchQuery, ResearchService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=["init-db", "sync", "check-research", "review-source", "approve-source"]
    )
    parser.add_argument("--source")
    parser.add_argument("--fingerprint")
    parser.add_argument("--latitude", type=float, default=32.7767)
    parser.add_argument("--longitude", type=float, default=-96.7970)
    args = parser.parse_args()
    settings = Settings()
    engine, factory = database(settings.database_url)
    try:
        if args.command in {"review-source", "approve-source"}:
            if not args.source:
                parser.error("--source is required")
            with factory() as session, session.begin():
                run = session.scalar(
                    select(SourceRun)
                    .where(SourceRun.source == args.source)
                    .order_by(SourceRun.finished_at.desc(), SourceRun.id.desc())
                    .limit(1)
                )
                if run is None or run.status != "review_required":
                    raise SystemExit("No quarantined source refresh to review")
                if args.command == "approve-source":
                    if args.fingerprint != run.fingerprint or run.finished_at < time.time() - 86400:
                        raise SystemExit(
                            "Exact current fingerprint from a review within 24 hours is required"
                        )
                    run.approved = True
                print(
                    json.dumps(
                        {
                            "source": run.source,
                            "fingerprint": run.fingerprint,
                            "candidate_count": run.record_count,
                            "removed_count": run.removed_count,
                            "approved": run.approved,
                            "message": run.message,
                        }
                    )
                )
        elif args.command == "check-research":
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
            print(
                f"Beta schema version {SCHEMA_VERSION} ready; retired Saved tables removed; "
                "accounts, sessions and source listings preserved"
            )
        else:
            result = asyncio.run(Catalog(factory).refresh())
            print(json.dumps(result, indent=2))
            if any(source["automated"] and source["status"] != "ready" for source in result):
                raise SystemExit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
