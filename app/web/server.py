from __future__ import annotations

import argparse
import json
import mimetypes
import socket
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from app.services import storage, system_info


STATIC_DIR = Path(__file__).resolve().parent / "static"


class VisoMasterWebHandler(BaseHTTPRequestHandler):
    server_version = "VisoMasterWeb/0.1"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_common_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._serve_static("index.html")
            return
        if path.startswith("/static/"):
            self._serve_static(path.removeprefix("/static/"))
            return
        if path == "/api/status":
            self._write_json(HTTPStatus.OK, system_info.system_status())
            return
        if path == "/api/jobs":
            self._write_json(HTTPStatus.OK, {"items": storage.list_jobs()})
            return
        if path == "/api/job-exports":
            self._write_json(HTTPStatus.OK, {"items": storage.list_job_exports()})
            return
        if path == "/api/presets":
            self._write_json(HTTPStatus.OK, {"items": storage.list_presets()})
            return
        if path == "/api/embeddings":
            self._write_json(HTTPStatus.OK, {"items": storage.list_embeddings()})
            return
        if path == "/api/workspaces/last":
            self._write_json(
                HTTPStatus.OK,
                {
                    "summary": storage.summarize_workspace(),
                    "data": storage.read_last_workspace(),
                },
            )
            return
        if path.startswith("/api/jobs/"):
            self._read_named_payload(storage.read_job, path.removeprefix("/api/jobs/"))
            return
        if path.startswith("/api/job-exports/"):
            self._read_named_payload(
                storage.read_job_export, path.removeprefix("/api/job-exports/")
            )
            return
        if path.startswith("/api/presets/"):
            self._read_named_payload(
                storage.read_preset, path.removeprefix("/api/presets/")
            )
            return
        if path.startswith("/api/embeddings/"):
            self._read_named_payload(
                storage.read_embedding, path.removeprefix("/api/embeddings/")
            )
            return

        self._write_json(HTTPStatus.NOT_FOUND, {"error": "Route nicht gefunden."})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        payload = self._read_request_json()
        if payload is None:
            return

        try:
            if path == "/api/workspaces/last":
                payload = self._require_json_object(
                    payload, "Der Arbeitsbereich muss als JSON-Objekt gesendet werden."
                )
                saved_path = storage.write_last_workspace(payload)
                self._write_json(
                    HTTPStatus.OK,
                    {
                        "message": "Letzter Arbeitsbereich gespeichert.",
                        "path": str(saved_path),
                    },
                )
                return
            if path.startswith("/api/jobs/"):
                name = unquote(path.removeprefix("/api/jobs/"))
                saved_path = storage.write_job(name, payload)
                self._write_json(
                    HTTPStatus.OK,
                    {"message": "Job gespeichert.", "path": str(saved_path)},
                )
                return
            if path.startswith("/api/job-exports/"):
                name = unquote(path.removeprefix("/api/job-exports/"))
                saved_path = storage.write_job_export(name, payload)
                self._write_json(
                    HTTPStatus.OK,
                    {"message": "Job-Export gespeichert.", "path": str(saved_path)},
                )
                return
            if path.startswith("/api/presets/"):
                name = unquote(path.removeprefix("/api/presets/"))
                payload = self._require_json_object(
                    payload, "Ein Preset muss als JSON-Objekt gesendet werden."
                )
                parameters = payload.get("parameters", {})
                control = payload.get("control", {})
                saved_paths = storage.write_preset(name, parameters, control)
                self._write_json(
                    HTTPStatus.OK,
                    {
                        "message": "Preset gespeichert.",
                        "paths": {key: str(value) for key, value in saved_paths.items()},
                    },
                )
                return
            if path.startswith("/api/embeddings/"):
                name = unquote(path.removeprefix("/api/embeddings/"))
                saved_path = storage.write_embedding(name, payload)
                self._write_json(
                    HTTPStatus.OK,
                    {"message": "Embedding gespeichert.", "path": str(saved_path)},
                )
                return
        except ValueError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        self._write_json(HTTPStatus.NOT_FOUND, {"error": "Route nicht gefunden."})

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path.startswith("/api/jobs/"):
                storage.delete_job(unquote(path.removeprefix("/api/jobs/")))
                self._write_json(HTTPStatus.OK, {"message": "Job gelöscht."})
                return
            if path.startswith("/api/job-exports/"):
                storage.delete_job_export(
                    unquote(path.removeprefix("/api/job-exports/"))
                )
                self._write_json(HTTPStatus.OK, {"message": "Job-Export gelöscht."})
                return
            if path.startswith("/api/presets/"):
                storage.delete_preset(unquote(path.removeprefix("/api/presets/")))
                self._write_json(HTTPStatus.OK, {"message": "Preset gelöscht."})
                return
            if path.startswith("/api/embeddings/"):
                storage.delete_embedding(unquote(path.removeprefix("/api/embeddings/")))
                self._write_json(HTTPStatus.OK, {"message": "Embedding gelöscht."})
                return
        except FileNotFoundError:
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "Eintrag nicht gefunden."})
            return
        except ValueError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        self._write_json(HTTPStatus.NOT_FOUND, {"error": "Route nicht gefunden."})

    def _read_named_payload(self, reader, raw_name: str) -> None:
        try:
            payload = reader(unquote(raw_name))
        except FileNotFoundError:
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "Eintrag nicht gefunden."})
            return
        except ValueError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self._write_json(HTTPStatus.OK, payload)

    def _read_request_json(self) -> Any | None:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Request-Body fehlt."})
            return None
        raw = self.rfile.read(content_length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {"error": f"Ungültiger JSON-Inhalt: {exc.msg}."},
            )
            return None

    def _require_json_object(self, payload: Any, error_message: str) -> dict:
        if not isinstance(payload, dict):
            raise ValueError(error_message)
        return payload

    def _serve_static(self, relative_path: str) -> None:
        target = (STATIC_DIR / relative_path).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "Statische Datei nicht gefunden."})
            return

        mime_type, _ = mimetypes.guess_type(target.name)
        self.send_response(HTTPStatus.OK)
        self._send_common_headers()
        self.send_header("Content-Type", mime_type or "application/octet-stream")
        self.end_headers()
        with target.open("rb") as handle:
            self.wfile.write(handle.read())

    def _write_json(self, status: HTTPStatus, payload: Any) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self._send_common_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_common_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")

    def log_message(self, format: str, *args) -> None:
        client_ip = self.client_address[0] if self.client_address else "unknown"
        print(f"[web] {client_ip} - {format % args}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Start the VisoMaster browser-accessible control server."
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to. Use 127.0.0.1 for local-only access or 0.0.0.0 for LAN access.",
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="TCP port for the local web server."
    )
    return parser


def _discover_local_ipv4_addresses() -> list[str]:
    addresses: set[str] = set()

    try:
        hostname = socket.gethostname()
        for family, _, _, _, sockaddr in socket.getaddrinfo(hostname, None):
            if family != socket.AF_INET:
                continue
            ip = sockaddr[0]
            if not ip.startswith("127."):
                addresses.add(ip)
    except OSError:
        pass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if not ip.startswith("127."):
                addresses.add(ip)
    except OSError:
        pass

    return sorted(addresses)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), VisoMasterWebHandler)
    if args.host == "0.0.0.0":
        print(f"VisoMaster web UI listening on all interfaces at port {args.port}")
        print(f"Local URL: http://127.0.0.1:{args.port}")
        for ip in _discover_local_ipv4_addresses():
            print(f"LAN URL:   http://{ip}:{args.port}")
    else:
        print(f"VisoMaster web UI listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
