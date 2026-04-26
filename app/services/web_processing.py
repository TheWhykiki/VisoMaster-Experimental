from __future__ import annotations

import importlib.util
import json
import os
import platform
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
RUNNER_BOOT_TIMEOUT_SECONDS = 120
RUNNER_STOP_TIMEOUT_SECONDS = 15
TERMINAL_STATUSES = {"succeeded", "failed", "stopped"}
RUNTIME_DEPENDENCIES = {
    "PySide6": "PySide6",
    "torch": "torch",
    "cv2": "opencv-python",
    "onnxruntime": "onnxruntime",
    "numpy": "numpy",
    "PIL": "Pillow",
    "huggingface_hub": "huggingface-hub",
    "imageio_ffmpeg": "imageio-ffmpeg",
}

_LOCK = threading.RLock()
_PROCESS: subprocess.Popen[str] | None = None
_PROCESS_LOG_HANDLE = None


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
        "Headless-Runner wird vorbereitet.",
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


def _iso_timestamp_age_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - parsed).total_seconds()
    except ValueError:
        return None


def _runner_boot_is_stale(status: dict[str, Any]) -> bool:
    if status.get("status") not in {"starting", "loading"}:
        return False
    if status.get("runnerStarted") or status.get("processingStarted"):
        return False
    age_seconds = _iso_timestamp_age_seconds(str(status.get("startedAt", "")))
    return bool(
        age_seconds is not None and age_seconds >= RUNNER_BOOT_TIMEOUT_SECONDS
    )


def _popen_creation_kwargs() -> dict[str, Any]:
    if platform.system() == "Windows":
        return {
            "creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        }
    return {"start_new_session": True}


def _terminate_pid_tree(pid: int | None, timeout: int = RUNNER_STOP_TIMEOUT_SECONDS) -> None:
    if not pid or pid <= 0:
        return
    if platform.system() == "Windows":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return

    try:
        os.killpg(pid, signal.SIGTERM)
    except OSError:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return

    deadline = time.time() + min(timeout, 5)
    while time.time() < deadline:
        if not _is_pid_running(pid):
            return
        time.sleep(0.1)

    try:
        os.killpg(pid, signal.SIGKILL)
    except OSError:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            return


def _terminate_process(
    process: subprocess.Popen[str] | None,
    pid: int | None,
    timeout: int = RUNNER_STOP_TIMEOUT_SECONDS,
) -> bool:
    target_pid = process.pid if process is not None else pid
    if process is not None and process.poll() is not None:
        return True

    try:
        _terminate_pid_tree(target_pid, timeout=timeout)
    except Exception:
        if process is not None and process.poll() is None:
            try:
                process.kill()
            except Exception:
                pass

    if process is not None:
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
        return process.poll() is not None

    deadline = time.time() + 2
    while time.time() < deadline:
        if not _is_pid_running(pid):
            return True
        time.sleep(0.1)
    return not _is_pid_running(pid)


def _active_process() -> subprocess.Popen[str] | None:
    global _PROCESS, _PROCESS_LOG_HANDLE
    current_file_status = _read_json_file(STATUS_FILE).get("status")
    if _PROCESS is not None and current_file_status in TERMINAL_STATUSES:
        _terminate_process(_PROCESS, None)
        _PROCESS = None
        _close_process_log_handle()
        return None
    if _PROCESS is not None and _PROCESS.poll() is not None:
        _PROCESS = None
        if _PROCESS_LOG_HANDLE is not None:
            _PROCESS_LOG_HANDLE.close()
            _PROCESS_LOG_HANDLE = None
    return _PROCESS


def _close_process_log_handle() -> None:
    global _PROCESS_LOG_HANDLE
    if _PROCESS_LOG_HANDLE is not None:
        _PROCESS_LOG_HANDLE.close()
        _PROCESS_LOG_HANDLE = None


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
    is_terminal = normalized.get("status") in TERMINAL_STATUSES
    normalized["active"] = False if is_terminal else process_running

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


def _fail_stale_runner(status: dict[str, Any]) -> dict[str, Any]:
    global _PROCESS
    pid = status.get("pid")
    _terminate_process(_PROCESS, pid)
    _PROCESS = None
    _close_process_log_handle()
    status.update(
        {
            "status": "failed",
            "message": (
                "Der Headless-Runner hat den Start nicht bestaetigt. "
                "Der Prozess wurde beendet; pruefe runner.log und starte den Web-Host neu, "
                "falls Windows noch eine alte Verarbeitung anzeigt."
            ),
            "finishedAt": _iso_now(),
            "staleRunnerKilled": True,
        }
    )
    return _persist_status(status)


def _persist_status(status: dict[str, Any]) -> dict[str, Any]:
    status["updatedAt"] = _iso_now()
    _write_json_file(STATUS_FILE, status)
    return status


def current_status() -> dict[str, Any]:
    with _LOCK:
        status = _read_json_file(STATUS_FILE)
        if _runner_boot_is_stale(status):
            status = _fail_stale_runner(status)
        return _normalize_status(status)


def _build_start_command(job_name: str) -> list[str]:
    return [
        sys.executable,
        "-m",
        "app.web.headless_runner_bootstrap",
        "--job",
        job_name,
        "--status-file",
        str(STATUS_FILE),
    ]


def _build_request_command(request_file: Path, status_file: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "app.web.headless_runner_bootstrap",
        "--request-file",
        str(request_file),
        "--status-file",
        str(status_file),
    ]


def _prepare_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    try:
        import imageio_ffmpeg

        ffmpeg_path = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if ffmpeg_path.is_file():
            ffmpeg_dir = str(ffmpeg_path.parent)
            env_path = env.get("PATH", "")
            if ffmpeg_dir not in env_path.split(os.pathsep):
                env["PATH"] = os.pathsep.join([ffmpeg_dir, env_path])
    except Exception:
        pass
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

        _close_process_log_handle()
        log_handle = LOG_FILE.open("w", encoding="utf-8")
        try:
            process = subprocess.Popen(
                _build_start_command(job_name),
                cwd=project_root_path(),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                env=_prepare_environment(),
                **_popen_creation_kwargs(),
            )
        except Exception:
            log_handle.close()
            raise

        global _PROCESS, _PROCESS_LOG_HANDLE
        _PROCESS = process
        _PROCESS_LOG_HANDLE = log_handle
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

        _close_process_log_handle()
        log_handle = LOG_FILE.open("w", encoding="utf-8")
        try:
            process = subprocess.Popen(
                _build_request_command(request_file, STATUS_FILE),
                cwd=project_root_path(),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                env=_prepare_environment(),
                **_popen_creation_kwargs(),
            )
        except Exception:
            log_handle.close()
            raise

        global _PROCESS, _PROCESS_LOG_HANDLE
        _PROCESS = process
        _PROCESS_LOG_HANDLE = log_handle
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

        stopped = _terminate_process(process, pid)
        global _PROCESS
        _PROCESS = None
        _close_process_log_handle()

        if not stopped and _is_pid_running(pid):
            status.update(
                {
                    "status": "failed",
                    "message": (
                        "Stop wurde angefordert, aber der Headless-Prozess laeuft "
                        f"weiter (PID {pid}). Bitte den Prozess auf dem Host beenden."
                    ),
                    "finishedAt": _iso_now(),
                }
            )
            _persist_status(status)
            return _normalize_status(status)

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
