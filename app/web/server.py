from __future__ import annotations

import argparse
import json
import mimetypes
import socket
from email.parser import BytesParser
from email.policy import default as email_policy
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from app.services import (
    browser_workflow,
    storage,
    system_info,
    web_processing,
    web_workbench,
)


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
        if path == "/api/processing/status":
            self._write_json(HTTPStatus.OK, web_processing.current_status())
            return
        if path == "/api/browser-workflow":
            self._write_json(HTTPStatus.OK, browser_workflow.current_state())
            return
        if path == "/api/browser-workflow/media/target":
            try:
                self._serve_file(browser_workflow.target_media_path())
            except FileNotFoundError:
                self._write_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "Es wurde noch kein Zielmedium hochgeladen."},
                )
            return
        if path.startswith("/api/browser-workflow/media/sources/"):
            try:
                name = unquote(path.removeprefix("/api/browser-workflow/media/sources/"))
                self._serve_file(browser_workflow.source_media_path(name))
            except FileNotFoundError:
                self._write_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "Das Quellgesicht wurde nicht gefunden."},
                )
            return
        if path == "/api/browser-workflow/preview/frame":
            try:
                self._serve_file(browser_workflow.preview_image_path())
            except FileNotFoundError:
                self._write_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "Es liegt noch keine Ziel-Frame-Vorschau vor."},
                )
            return
        if path == "/api/browser-workflow/preview/swap":
            try:
                self._serve_file(browser_workflow.swap_preview_image_path())
            except FileNotFoundError:
                self._write_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "Es liegt noch keine geswappte Vorschau vor."},
                )
            return
        if path.startswith("/api/browser-workflow/faces/"):
            try:
                name = unquote(path.removeprefix("/api/browser-workflow/faces/"))
                self._serve_file(browser_workflow.detected_face_image_path(name))
            except FileNotFoundError:
                self._write_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "Das gefundene Zielgesicht wurde nicht gefunden."},
                )
            return
        if path == "/api/workbench":
            self._write_json(HTTPStatus.OK, web_workbench.schema_payload())
            return
        if path == "/api/processing/output":
            output_path = web_processing.current_output_path()
            if output_path is None:
                self._write_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "Es liegt noch keine fertige Ausgabedatei vor."},
                )
                return
            self._serve_file(output_path)
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

        if path == "/api/processing/stop":
            try:
                payload = web_processing.stop_job()
            except ValueError as exc:
                self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            self._write_json(HTTPStatus.OK, payload)
            return

        if path.startswith("/api/processing/jobs/") and path.endswith("/start"):
            raw_name = path.removeprefix("/api/processing/jobs/").removesuffix("/start")
            job_name = unquote(raw_name.rstrip("/"))
            try:
                payload = web_processing.start_job(job_name)
            except FileNotFoundError:
                self._write_json(HTTPStatus.NOT_FOUND, {"error": "Job nicht gefunden."})
                return
            except ValueError as exc:
                self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            self._write_json(HTTPStatus.ACCEPTED, payload)
            return

        if path == "/api/browser-workflow/reset":
            payload = browser_workflow.reset()
            self._write_json(HTTPStatus.OK, payload)
            return

        if path == "/api/browser-workflow/faces/clear":
            browser_workflow.clear_detected_faces()
            self._write_json(
                HTTPStatus.OK,
                {
                    "message": "Gefundene Zielgesichter wurden geleert.",
                    "state": browser_workflow.current_state(),
                },
            )
            return

        if path == "/api/browser-workflow/run":
            payload = self._read_request_json()
            if payload is None:
                return
            try:
                detection_frame = int(payload.get("detectionFrame", 0))
                response = web_processing.start_upload_run(
                    detection_frame=detection_frame,
                    workbench_state=payload.get("workbench"),
                )
            except ValueError as exc:
                self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            self._write_json(HTTPStatus.ACCEPTED, response)
            return

        if path == "/api/browser-workflow/preview/frame":
            payload = self._read_request_json()
            if payload is None:
                return
            try:
                preview = browser_workflow.generate_target_preview(
                    int(payload.get("frameIndex", 0))
                )
            except (FileNotFoundError, ValueError) as exc:
                self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            self._write_json(
                HTTPStatus.OK,
                {
                    "message": "Ziel-Frame-Vorschau aktualisiert.",
                    "previewFrame": preview,
                    "state": browser_workflow.current_state(),
                },
            )
            return

        if path == "/api/browser-workflow/preview/swap":
            payload = self._read_request_json()
            if payload is None:
                return
            try:
                response = web_processing.generate_upload_preview(
                    detection_frame=int(payload.get("frameIndex", 0)),
                    workbench_state=payload.get("workbench"),
                )
            except ValueError as exc:
                self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            self._write_json(HTTPStatus.OK, response)
            return

        if path == "/api/browser-workflow/find-faces":
            payload = self._read_request_json()
            if payload is None:
                return
            try:
                response = web_processing.generate_found_faces(
                    detection_frame=int(payload.get("frameIndex", 0)),
                    workbench_state=payload.get("workbench"),
                )
            except ValueError as exc:
                self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            self._write_json(HTTPStatus.OK, response)
            return

        if path == "/api/browser-workflow/target":
            try:
                uploads = self._read_request_files()
                if len(uploads) != 1:
                    raise ValueError("Bitte genau ein Zielmedium hochladen.")
                filename, content = uploads[0]
                response = browser_workflow.save_target_upload(filename, content)
            except ValueError as exc:
                self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            self._write_json(HTTPStatus.OK, response)
            return

        if path == "/api/browser-workflow/sources":
            try:
                uploads = self._read_request_files()
                response = browser_workflow.save_source_uploads(uploads)
            except ValueError as exc:
                self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            self._write_json(HTTPStatus.OK, response)
            return

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
            if path == "/api/workbench":
                payload = self._require_json_object(
                    payload, "Der Workbench-Status muss als JSON-Objekt gesendet werden."
                )
                state = web_workbench.write_state(payload)
                self._write_json(
                    HTTPStatus.OK,
                    {
                        "message": "Workbench-Draft gespeichert.",
                        "state": state,
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

    def _read_request_files(self) -> list[tuple[str, bytes]]:
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            raise ValueError("Datei-Uploads muessen als multipart/form-data gesendet werden.")

        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise ValueError("Es wurden keine Dateien uebertragen.")

        raw_body = self.rfile.read(content_length)
        message = BytesParser(policy=email_policy).parsebytes(
            (
                f"Content-Type: {content_type}\r\n"
                "MIME-Version: 1.0\r\n"
                "\r\n"
            ).encode("utf-8")
            + raw_body
        )

        uploads: list[tuple[str, bytes]] = []
        for part in message.iter_parts():
            if part.get_content_disposition() != "form-data":
                continue
            field_name = part.get_param("name", header="content-disposition")
            if field_name not in {"files", "file"}:
                continue
            filename = part.get_filename()
            if not filename:
                continue
            uploads.append((filename, part.get_payload(decode=True) or b""))

        if not uploads:
            raise ValueError("Es wurden keine Dateien uebertragen.")
        return uploads

    def _serve_static(self, relative_path: str) -> None:
        target = (STATIC_DIR / relative_path).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "Statische Datei nicht gefunden."})
            return

        self._serve_file(target)

    def _serve_file(self, target: Path) -> None:
        mime_type, _ = mimetypes.guess_type(target.name)
        self.send_response(HTTPStatus.OK)
        self._send_common_headers()
        self.send_header("Content-Type", mime_type or "application/octet-stream")
        self.send_header("Content-Length", str(target.stat().st_size))
        self.send_header(
            "Content-Disposition", f'inline; filename="{target.name}"'
        )
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
