from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status_file_from_argv(argv: list[str]) -> Path | None:
    for index, value in enumerate(argv):
        if value == "--status-file" and index + 1 < len(argv):
            return Path(argv[index + 1])
    return None


def _write_status(path: Path | None, **updates) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {}
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
    if not isinstance(payload, dict):
        payload = {}
    payload.update(updates)
    payload["updatedAt"] = _iso_now()
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp_path.replace(path)


def main() -> int:
    status_file = _status_file_from_argv(sys.argv)
    _write_status(
        status_file,
        status="loading",
        message="Headless-Runner importiert Desktop-Komponenten.",
        pid=os.getpid(),
        runnerBootstrapped=True,
        runnerBootstrapAt=_iso_now(),
    )
    try:
        from app.web import headless_runner
    except Exception as exc:
        _write_status(
            status_file,
            status="failed",
            message=f"Headless-Runner konnte nicht importiert werden: {exc}",
            pid=os.getpid(),
            runnerBootstrapped=True,
            importTraceback=traceback.format_exc(),
            finishedAt=_iso_now(),
        )
        traceback.print_exc()
        return 1
    return headless_runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
