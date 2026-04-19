from __future__ import annotations

import importlib.util
import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.helpers.paths import ensure_project_dir, project_root_path
from app.services import browser_workflow, storage


PROCESSING_DIR = ensure_project_dir(".web", "processing")
STATUS_FILE = PROCESSING_DIR / "status.json"
PREVIEW_STATUS_FILE = PROCESSING_DIR / "preview_status.json"
LOG_FILE = PROCESSING_DIR / "runner.log"
PREVIEW_LOG_FILE = PROCESSING_DIR / "preview_runner.log"
LOG_TAIL_LINE_COUNT = 40
RUNTIME_DEPENDENCIES = {
    "PySide6": "PySide6",
    "torch": "torch",
    "cv2": "opencv-python",
    "onnxruntime": "onnxruntime",
    "numpy": "numpy",
    "PIL": "Pillow",
}

_LOCK = threading.RLock()
_PROCESS: subprocess.Popen[str] | None = None


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    temp_path.replace(path)


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def _read_log_tail(path: Path, limit: int = LOG_TAIL_LINE_COUNT) -> list[str]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        lines = handle.readlines()
    return [line.rstrip() for line in lines[-limit:] if line.strip()]


def _detailed_failure_message(
    status_file: Path,
    log_file: Path,
    fallback: str,
) -> str:
    status = _read_json_file(status_file)
    message = str(status.get("message", "")).strip()
    if message and message not in {
        "Geswappte Vorschau wird erzeugt.",
        "Zielgesichter werden im Browser-Workflow gesucht.",
        "Browser-Direktlauf wird gestartet.",
    }:
        return message

    log_tail = _read_log_tail(log_file, limit=12)
    if log_tail:
        return log_tail[-1]
    return fallback


def _ensure_runtime_dependencies() -> None:
    missing = [
        package_name
        for module_name, package_name in RUNTIME_DEPENDENCIES.items()
        if importlib.util.find_spec(module_name) is None
    ]
    if missing:
        raise ValueError(
            "Die aktive Web-Runtime ist unvollstaendig. "
            f"Fehlende Python-Pakete: {', '.join(missing)}. "
            "Bitte den Web-Host mit Start_Web_Network.bat oder Start_Web.bat neu starten."
        )


def _is_pid_running(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _active_process() -> subprocess.Popen[str] | None:
    global _PROCESS
    if _PROCESS is not None and _PROCESS.poll() is not None:
        _PROCESS = None
    return _PROCESS


def _status_template() -> dict[str, Any]:
    return {
        "status": "idle",
        "message": "Noch keine Browser-Verarbeitung gestartet.",
        "updatedAt": _iso_now(),
    }


def _normalize_status(status: dict[str, Any]) -> dict[str, Any]:
    normalized = _status_template()
    normalized.update(status)

    log_tail = _read_log_tail(LOG_FILE)
    normalized["logPath"] = str(LOG_FILE)
    normalized["logTail"] = log_tail

    pid = normalized.get("pid")
    process_running = _is_pid_running(pid)
    normalized["active"] = process_running

    transient_states = {"starting", "loading", "running", "stopping"}
    if normalized["status"] in transient_states and not process_running:
        normalized["status"] = "failed"
        normalized["message"] = normalized.get(
            "message",
            "Der Hintergrundprozess wurde unerwartet beendet.",
        )

    output_path = normalized.get("outputPath")
    if output_path:
        output_file = Path(output_path)
        normalized["outputExists"] = output_file.is_file()
        normalized["outputName"] = output_file.name
        if output_file.is_file():
            normalized["outputDownloadUrl"] = "/api/processing/output"
    else:
        normalized["outputExists"] = False

    return normalized


def _persist_status(status: dict[str, Any]) -> dict[str, Any]:
    status["updatedAt"] = _iso_now()
    _write_json_file(STATUS_FILE, status)
    return status


def current_status() -> dict[str, Any]:
    with _LOCK:
        return _normalize_status(_read_json_file(STATUS_FILE))


def _build_start_command(job_name: str) -> list[str]:
    return [
        sys.executable,
        "-m",
        "app.web.headless_runner",
        "--job",
        job_name,
        "--status-file",
        str(STATUS_FILE),
    ]


def _build_request_command(request_file: Path, status_file: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "app.web.headless_runner",
        "--request-file",
        str(request_file),
        "--status-file",
        str(status_file),
    ]


def _prepare_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    return env


def start_job(job_name: str) -> dict[str, Any]:
    storage.read_job(job_name)
    _ensure_runtime_dependencies()

    with _LOCK:
        active = _active_process()
        if active is not None and active.poll() is None:
            raise ValueError("Es laeuft bereits eine Browser-Verarbeitung.")

        PROCESSING_DIR.mkdir(parents=True, exist_ok=True)
        if LOG_FILE.exists():
            LOG_FILE.unlink()

        initial_status = _persist_status(
            {
                "status": "starting",
                "jobName": job_name,
                "message": f'Browser-Verarbeitung fuer Job "{job_name}" wird gestartet.',
                "startedAt": _iso_now(),
                "statusFile": str(STATUS_FILE),
            }
        )

        with LOG_FILE.open("w", encoding="utf-8") as log_handle:
            process = subprocess.Popen(
                _build_start_command(job_name),
                cwd=project_root_path(),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                env=_prepare_environment(),
            )

        global _PROCESS
        _PROCESS = process
        initial_status["pid"] = process.pid
        initial_status["message"] = (
            f'Browser-Verarbeitung fuer Job "{job_name}" wurde gestartet.'
        )
        _persist_status(initial_status)
        return _normalize_status(initial_status)


def start_upload_run(
    detection_frame: int = 0,
    workbench_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ensure_runtime_dependencies()
    request_payload = browser_workflow.build_run_request(
        detection_frame=detection_frame,
        workbench_state=workbench_state,
    )

    with _LOCK:
        active = _active_process()
        if active is not None and active.poll() is None:
            raise ValueError("Es laeuft bereits eine Browser-Verarbeitung.")

        PROCESSING_DIR.mkdir(parents=True, exist_ok=True)
        if LOG_FILE.exists():
            LOG_FILE.unlink()

        request_file = PROCESSING_DIR / "current_request.json"
        _write_json_file(request_file, request_payload)

        initial_status = _persist_status(
            {
                "status": "starting",
                "mode": "upload",
                "message": "Browser-Direktlauf wird gestartet.",
                "startedAt": _iso_now(),
                "statusFile": str(STATUS_FILE),
                "requestFile": str(request_file),
                "targetMediaPath": request_payload["targetMediaPath"],
                "inputFaceCount": len(request_payload["inputFacePaths"]),
            }
        )

        with LOG_FILE.open("w", encoding="utf-8") as log_handle:
            process = subprocess.Popen(
                _build_request_command(request_file, STATUS_FILE),
                cwd=project_root_path(),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                env=_prepare_environment(),
            )

        global _PROCESS
        _PROCESS = process
        initial_status["pid"] = process.pid
        initial_status["message"] = "Browser-Direktlauf wurde gestartet."
        _persist_status(initial_status)
        return _normalize_status(initial_status)


def generate_upload_preview(
    detection_frame: int = 0,
    workbench_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ensure_runtime_dependencies()
    request_payload = browser_workflow.build_run_request(
        detection_frame=detection_frame,
        workbench_state=workbench_state,
    )
    request_payload["mode"] = "preview"
    request_payload["label"] = "Browser-Swap-Vorschau"
    preview_output_path = browser_workflow.swap_preview_output_path()
    request_payload["previewOutputPath"] = str(preview_output_path)

    with _LOCK:
        active = _active_process()
        if active is not None and active.poll() is None:
            raise ValueError("Es laeuft bereits eine Browser-Verarbeitung.")

        PROCESSING_DIR.mkdir(parents=True, exist_ok=True)
        browser_workflow.clear_swap_preview()

        request_file = PROCESSING_DIR / "current_preview_request.json"
        _write_json_file(request_file, request_payload)

        preview_status = {
            "status": "starting",
            "mode": "preview",
            "message": "Geswappte Vorschau wird erzeugt.",
            "startedAt": _iso_now(),
            "targetMediaPath": request_payload["targetMediaPath"],
            "inputFaceCount": len(request_payload["inputFacePaths"]),
            "statusFile": str(PREVIEW_STATUS_FILE),
            "requestFile": str(request_file),
        }
        _write_json_file(PREVIEW_STATUS_FILE, preview_status)
        if PREVIEW_LOG_FILE.exists():
            PREVIEW_LOG_FILE.unlink()

        with PREVIEW_LOG_FILE.open("w", encoding="utf-8") as log_handle:
            process = subprocess.run(
                _build_request_command(request_file, PREVIEW_STATUS_FILE),
                cwd=project_root_path(),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                env=_prepare_environment(),
            )

        final_status = _read_json_file(PREVIEW_STATUS_FILE)
        if process.returncode != 0:
            message = _detailed_failure_message(
                PREVIEW_STATUS_FILE,
                PREVIEW_LOG_FILE,
                "Die geswappte Vorschau konnte nicht erzeugt werden.",
            )
            raise ValueError(message)
        if final_status.get("status") != "succeeded":
            message = final_status.get(
                "message",
                "Die geswappte Vorschau wurde nicht erfolgreich abgeschlossen.",
            )
            raise ValueError(message)

        browser_workflow.register_swap_preview(
            preview_output_path,
            frame_index=int(request_payload.get("detectionFrame", 0)),
            source_count=len(request_payload["inputFacePaths"]),
        )
        return {
            "message": "Geswappte Vorschau wurde erzeugt.",
            "state": browser_workflow.current_state(),
        }


def generate_found_faces(
    detection_frame: int = 0,
    workbench_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ensure_runtime_dependencies()
    request_payload = browser_workflow.build_find_faces_request(
        detection_frame=detection_frame,
        workbench_state=workbench_state,
    )

    with _LOCK:
        active = _active_process()
        if active is not None and active.poll() is None:
            raise ValueError("Es laeuft bereits eine Browser-Verarbeitung.")

        PROCESSING_DIR.mkdir(parents=True, exist_ok=True)
        browser_workflow.clear_detected_faces()
        browser_workflow.clear_swap_preview()

        request_file = PROCESSING_DIR / "current_find_faces_request.json"
        _write_json_file(request_file, request_payload)

        preview_status = {
            "status": "starting",
            "mode": "find_faces",
            "message": "Zielgesichter werden im Browser-Workflow gesucht.",
            "startedAt": _iso_now(),
            "targetMediaPath": request_payload["targetMediaPath"],
            "statusFile": str(PREVIEW_STATUS_FILE),
            "requestFile": str(request_file),
        }
        _write_json_file(PREVIEW_STATUS_FILE, preview_status)
        if PREVIEW_LOG_FILE.exists():
            PREVIEW_LOG_FILE.unlink()

        with PREVIEW_LOG_FILE.open("w", encoding="utf-8") as log_handle:
            process = subprocess.run(
                _build_request_command(request_file, PREVIEW_STATUS_FILE),
                cwd=project_root_path(),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                env=_prepare_environment(),
            )

        final_status = _read_json_file(PREVIEW_STATUS_FILE)
        if process.returncode != 0:
            message = _detailed_failure_message(
                PREVIEW_STATUS_FILE,
                PREVIEW_LOG_FILE,
                "Die Zielgesicht-Suche konnte nicht abgeschlossen werden.",
            )
            raise ValueError(message)
        if final_status.get("status") != "succeeded":
            message = final_status.get(
                "message",
                "Die Zielgesicht-Suche wurde nicht erfolgreich abgeschlossen.",
            )
            raise ValueError(message)

        manifest_path = browser_workflow.found_faces_manifest_path()
        manifest = _read_json_file(manifest_path)
        faces = manifest.get("faces") if isinstance(manifest, dict) else None
        if not isinstance(faces, list) or not faces:
            return {
                "message": "Im aktuellen Detection Frame wurden keine Zielgesichter gefunden.",
                "state": browser_workflow.current_state(),
            }

        detected = browser_workflow.register_detected_faces(manifest)
        return {
            "message": f'{detected["count"]} Zielgesicht(er) gefunden.',
            "state": browser_workflow.current_state(),
        }


def stop_job() -> dict[str, Any]:
    with _LOCK:
        status = _read_json_file(STATUS_FILE)
        pid = status.get("pid")
        process = _active_process()

        if process is None and not _is_pid_running(pid):
            raise ValueError("Es laeuft aktuell keine Browser-Verarbeitung.")

        status.update(
            {
                "status": "stopping",
                "message": "Browser-Verarbeitung wird gestoppt.",
            }
        )
        _persist_status(status)

        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            finally:
                global _PROCESS
                _PROCESS = None
        elif _is_pid_running(pid):
            os.kill(pid, signal.SIGTERM)

        status.update(
            {
                "status": "stopped",
                "message": "Browser-Verarbeitung wurde beendet.",
            }
        )
        _persist_status(status)
        return _normalize_status(status)


def current_output_path() -> Path | None:
    status = current_status()
    output_path = status.get("outputPath")
    if not output_path:
        return None

    candidate = Path(output_path)
    if not candidate.is_file():
        return None
    return candidate
