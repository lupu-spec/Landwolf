"""Ensure a failed migration or wrong environment cannot start the staging server."""

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "landwolf" / "start_staging.sh"


@pytest.mark.parametrize(
    ("environment", "migration_exit", "expected_exit", "server_started"),
    [("staging", 0, 0, True), ("staging", 23, 23, False), ("production", 0, 64, False)],
)
def test_staging_startup_fails_closed(
    tmp_path: Path,
    environment: str,
    migration_exit: int,
    expected_exit: int,
    server_started: bool,
) -> None:
    executable = tmp_path / "python"
    executable.write_text(
        "#!/bin/sh\n"
        'if [ "$2" = "landwolf.cli" ]; then exit "$MIGRATION_EXIT"; fi\n'
        'if [ "$2" = "landwolf.serve" ]; then : > "$START_MARKER"; exit 0; fi\n'
        "exit 99\n"
    )
    executable.chmod(0o700)
    marker = tmp_path / "started"
    environment_vars = {
        **os.environ,
        "PATH": str(tmp_path),
        "LANDWOLF_ENVIRONMENT": environment,
        "MIGRATION_EXIT": str(migration_exit),
        "START_MARKER": str(marker),
    }
    result = subprocess.run(
        ["/bin/sh", str(SCRIPT)],
        env=environment_vars,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == expected_exit
    assert marker.exists() is server_started
