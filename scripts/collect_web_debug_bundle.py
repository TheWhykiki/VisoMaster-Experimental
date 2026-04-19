from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
import sys
import threading
import urllib.request
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

from app.web.server import VisoMasterWebHandler


ROOT = Path(__file__).resolve().parents[1]
DEBUG_ROOT = ROOT / ".web" / "debug-bundles"


class QuietVisoMasterWebHandler(VisoMasterWebHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return None


def now_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def run_command(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return (completed.stdout or "") + (completed.stderr or "")


def fetch(url: str) -> tuple[str, bytes]:
    with urllib.request.urlopen(url, timeout=5) as response:
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        return content_type, response.read()


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def collect_static_contract(bundle_dir: Path) -> None:
    html = (ROOT / "app" / "web" / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "app" / "web" / "static" / "app.js").read_text(encoding="utf-8")
    html_ids = sorted(set(re.findall(r'id="([^"]+)"', html)))
    js_ids = sorted(set(re.findall(r'getElementById\("([^"]+)"\)', js)))
    missing_ids = sorted(set(js_ids) - set(html_ids))
    payload = {
        "htmlIdCount": len(html_ids),
        "jsIdCount": len(js_ids),
        "missingIds": missing_ids,
    }
    write_text(bundle_dir / "static-contract.json", json.dumps(payload, indent=2))


def copy_if_exists(source: Path, destination: Path) -> None:
    if source.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def main() -> int:
    bundle_dir = DEBUG_ROOT / now_slug()
    bundle_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "cwd": str(ROOT),
    }
    write_text(bundle_dir / "meta.json", json.dumps(metadata, indent=2))
    write_text(bundle_dir / "git-status.txt", run_command(["git", "status", "-sb"]))
    write_text(bundle_dir / "git-head.txt", run_command(["git", "rev-parse", "HEAD"]))
    write_text(bundle_dir / "python-compile.txt", run_command([sys.executable, "-m", "py_compile", "app/web/server.py", "app/web/headless_runner.py", "app/services/web_processing.py", "app/services/browser_workflow.py", "app/services/web_workbench.py"]))

    collect_static_contract(bundle_dir)

    copy_if_exists(ROOT / "app" / "web" / "static" / "index.html", bundle_dir / "static" / "index.html")
    copy_if_exists(ROOT / "app" / "web" / "static" / "app.js", bundle_dir / "static" / "app.js")
    copy_if_exists(ROOT / "app" / "web" / "static" / "styles.css", bundle_dir / "static" / "styles.css")
    copy_if_exists(ROOT / ".web" / "workflow" / "swap_workbench.json", bundle_dir / "runtime" / "swap_workbench.json")
    copy_if_exists(ROOT / ".web" / "processing" / "status.json", bundle_dir / "runtime" / "status.json")
    copy_if_exists(ROOT / ".web" / "processing" / "runner.log", bundle_dir / "runtime" / "runner.log")

    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietVisoMasterWebHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        for endpoint, filename in (
            ("/", "root.html"),
            ("/api/status", "api-status.json"),
            ("/api/workbench", "api-workbench.json"),
            ("/api/browser-workflow", "api-browser-workflow.json"),
            ("/api/processing/status", "api-processing-status.json"),
        ):
            content_type, body = fetch(f"http://127.0.0.1:{port}{endpoint}")
            target = bundle_dir / "http" / filename
            if "json" in content_type:
                parsed = json.loads(body.decode("utf-8"))
                write_text(target, json.dumps(parsed, indent=2))
            else:
                write_bytes(target, body)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)

    print(f"Debug bundle written to {bundle_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
