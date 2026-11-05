"""Browser fixture replacing only the external factory transport; local auth/SQL are real."""

import base64
import hashlib
import uuid
from typing import Any

from fastapi import HTTPException
from pydantic import SecretStr

from landwolf import factory_bridge
from landwolf.config import Settings
from landwolf.main import create_app


def create_fixture_app():
    settings = Settings()
    if settings.environment != "test":
        raise RuntimeError("Synthetic factory requires test environment")
    settings.factory_token = SecretStr("test-only-factory-connection")
    jobs: dict[str, dict[str, Any]] = {}

    def exchange(settings, method, path, payload=None):
        if path == "/portal/targets":
            return {
                "runners": [
                    {
                        "name": "SYNTHETIC MACHINE",
                        "connected": True,
                        "ready": True,
                        "projects": [
                            {
                                "id": "new",
                                "name": "NEW PROJECT",
                                "runtimes": ["python"],
                                "checks": "syntax",
                            }
                        ],
                    }
                ]
            }
        key = path.split("/")[3]
        if method == "PUT" and key not in jobs:
            jobs[key] = {"id": key, "task_id": str(uuid.uuid4()), "state": "queued"}
            if payload["acceptance"] == "RETURN SYNTHETIC RESULT":
                jobs[key].update(
                    state="completed",
                    result={
                        "report": {"status": "SYNTAX_CHECKED"},
                        "patch": (
                            "--- a/main.py\n+++ b/main.py\n@@ -1 +1 @@\n-pass\n+print('fixture')\n"
                        ),
                    },
                )
            if payload["acceptance"] == "RETURN SYNTHETIC RELEASE":
                source = b"PK-synthetic-source"
                jobs[key].update(
                    state="completed",
                    release={
                        "id": str(uuid.uuid4()),
                        "version": "1.0.0",
                        "state": "delivered",
                        "target": "fixture-calculator",
                        "production_url": "https://fixture-calculator.pages.dev",
                        "source_sha256": hashlib.sha256(source).hexdigest(),
                        "artifact_sha256": "a" * 64,
                        "has_source": True,
                        "report": {
                            "schema": "l91.release-checks.v1",
                            "operation": "publish",
                            "passed": True,
                            "artifact_sha256": "a" * 64,
                        },
                    },
                )
            # Simulate a saved job followed by a lost network acknowledgement.
            raise HTTPException(503, "Factory unavailable; retry this request")
        if key not in jobs:
            raise HTTPException(404, "not received")
        if path.endswith("/cancel"):
            jobs[key]["state"] = "cancelled"
        if path.endswith("/source"):
            return {"base64": base64.b64encode(b"PK-synthetic-source").decode()}
        return jobs[key]

    factory_bridge.exchange = exchange
    return create_app(settings)
