"""Reproduce the raw collision, then prove the candidate fails before import."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from uk_bin_collection.uk_bin_collection.dependency_validation import (
    validate_websocket_client,
)
from uk_bin_collection.uk_bin_collection.exceptions import DependencyShadowingError


def main() -> None:
    evidence = Path(os.environ.get("UKBCD_TEST_EVIDENCE_DIR", "/evidence"))
    evidence.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp_dir:
        poison_root = Path(temp_dir)
        poison = poison_root / "websocket"
        poison.mkdir()
        execution_marker = poison_root / "poison_executed"
        (poison / "__init__.py").write_text(
            "from pathlib import Path\n"
            f"Path({str(execution_marker)!r}).write_text('executed')\n"
            "from ..const import DOMAIN\n",
            encoding="utf-8",
        )

        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(poison_root), env.get("PYTHONPATH", "")]
        )
        raw = subprocess.run(
            [
                sys.executable,
                "-c",
                "from selenium.webdriver.remote.websocket_connection import "
                "WebSocketConnection",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        raw_reproduced = (
            raw.returncode != 0
            and "attempted relative import beyond top-level package" in raw.stderr
            and execution_marker.exists()
        )

        execution_marker.unlink(missing_ok=True)
        sys.path.insert(0, str(poison_root))
        sys.modules.pop("websocket", None)
        try:
            validate_websocket_client()
        except DependencyShadowingError as exc:
            typed_error = type(exc).__name__
            typed_message = str(exc)
        else:
            typed_error = None
            typed_message = None
        finally:
            sys.path.remove(str(poison_root))

        candidate_blocked_before_execution = (
            typed_error == "DependencyShadowingError" and not execution_marker.exists()
        )

    report = {
        "raw_import_reproduced": raw_reproduced,
        "raw_return_code": raw.returncode,
        "candidate_error": typed_error,
        "candidate_message": typed_message,
        "candidate_blocked_before_poison_execution": candidate_blocked_before_execution,
    }
    (evidence / "collision_probe.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    if not raw_reproduced or not candidate_blocked_before_execution:
        raise SystemExit(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
