"""Rehearse PostgreSQL dump/restore on the disposable GitHub CI service only."""

import hashlib
import json
import os
import re
import subprocess

from sqlalchemy import MetaData, select
from sqlalchemy.engine import make_url

from landwolf.db import database


def digest_database(url: str) -> dict[str, str]:
    engine, _ = database(url)
    try:
        metadata = MetaData()
        metadata.reflect(engine)
        result = {}
        with engine.connect() as connection:
            for table in metadata.sorted_tables:
                rows = sorted(
                    json.dumps(dict(row), sort_keys=True, default=str)
                    for row in connection.execute(select(table)).mappings()
                )
                result[table.name] = hashlib.sha256("\n".join(rows).encode()).hexdigest()
        return result
    finally:
        engine.dispose()


def main() -> None:
    url = os.environ.get("LANDWOLF_TEST_POSTGRES_URL", "")
    container = os.environ.get("LANDWOLF_TEST_POSTGRES_CONTAINER", "")
    parsed = make_url(url) if url else None
    if (
        parsed is None
        or parsed.host not in {"localhost", "127.0.0.1"}
        or parsed.database != "landwolf_ci"
        or parsed.username != "landwolf_ci"
        or not re.fullmatch(r"[a-f0-9]{12,64}", container)
        or os.environ.get("GITHUB_ACTIONS") != "true"
    ):
        raise SystemExit("Requires the disposable landwolf_ci GitHub service container")

    def run(*args: str, data: bytes | None = None) -> bytes:
        return subprocess.run(
            ["docker", "exec", "-i", container, *args],
            input=data,
            capture_output=True,
            check=True,
            timeout=90,
        ).stdout

    before = digest_database(url)
    if not before or "lw2_saved_records" in before or "lw2_saved_properties" in before:
        raise RuntimeError("Disposable source database is not the expected migrated schema")
    dump = run("pg_dump", "-U", "landwolf_ci", "-d", "landwolf_ci", "-Fc")
    # If this database already exists, fail without deleting or changing it.
    run("createdb", "-U", "landwolf_ci", "landwolf_restore")
    try:
        run(
            "pg_restore",
            "-U",
            "landwolf_ci",
            "--exit-on-error",
            "--no-owner",
            "-d",
            "landwolf_restore",
            data=dump,
        )
        restored = parsed.set(database="landwolf_restore").render_as_string(hide_password=False)
        if digest_database(restored) != before:
            raise RuntimeError("Restored tables or row contents differ from the disposable source")
        print(f"Passed: pg_dump/pg_restore and exact row digests across {len(before)} tables")
    finally:
        run("dropdb", "-U", "landwolf_ci", "landwolf_restore")


if __name__ == "__main__":
    main()
