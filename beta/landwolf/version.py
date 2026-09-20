"""Public release identity; never expose arbitrary environment values."""

import os
import re

VERSION = "0.3.0"


def release(environment: str) -> dict[str, str | None]:
    commit = os.environ.get("RENDER_GIT_COMMIT", "")
    return {
        "version": VERSION,
        "environment": environment,
        "commit": commit if re.fullmatch(r"[0-9a-f]{40}", commit) else None,
    }
