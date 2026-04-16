from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.helpers.paths import ensure_project_dir, project_path


VALID_NAME_RE = re.compile(r"^[\w\- ]+$")


def jobs_dir() -> Path:
    return ensure_project_dir("jobs")


def job_exports_dir() -> Path:
    return ensure_project_dir(".jobs")


def presets_dir() -> Path:
    return ensure_project_dir("presets")


def last_workspace_path() -> Path:
    return project_path("last_workspace.json")


def validate_item_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Name must not be empty.")
    if not VALID_NAME_RE.match(cleaned):
        raise ValueError(
            "Name contains invalid characters. Only letters, numbers, spaces, dashes, and underscores are allowed."
        )
    return cleaned


def _read_json_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=4)
    temp_path.replace(path)


def _to_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _json_summary(path: Path, name: str, payload: dict[str, Any]) -> dict[str, Any]:
    stat = path.stat()
    return {
        "name": name,
        "path": str(path),
        "size": stat.st_size,
        "modifiedAt": _to_iso(stat.st_mtime),
        "targetMediaCount": len(payload.get("target_medias_data", [])),
        "inputFaceCount": len(payload.get("input_faces_data", {})),
        "targetFaceCount": len(payload.get("target_faces_data", {})),
        "embeddingCount": len(payload.get("embeddings_data", {})),
        "markerCount": len(payload.get("markers", {})),
    }


def _list_json_collection(base_dir: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(base_dir.glob("*.json")):
        try:
            payload = _read_json_file(path)
            items.append(_json_summary(path, path.stem, payload))
        except (OSError, json.JSONDecodeError):
            items.append(
                {
                    "name": path.stem,
                    "path": str(path),
                    "invalid": True,
                }
            )
    return items


def list_jobs() -> list[dict[str, Any]]:
    return _list_json_collection(jobs_dir())


def list_job_exports() -> list[dict[str, Any]]:
    return _list_json_collection(job_exports_dir())


def list_presets() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(presets_dir().glob("*.json")):
        if path.name.endswith("_ctl.json"):
            continue
        control_path = path.with_name(f"{path.stem}_ctl.json")
        stat = path.stat()
        items.append(
            {
                "name": path.stem,
                "path": str(path),
                "hasControlFile": control_path.is_file(),
                "size": stat.st_size,
                "modifiedAt": _to_iso(stat.st_mtime),
            }
        )
    return items


def read_job(name: str) -> dict[str, Any]:
    safe_name = validate_item_name(name)
    return _read_json_file(jobs_dir() / f"{safe_name}.json")


def write_job(name: str, payload: dict[str, Any]) -> Path:
    safe_name = validate_item_name(name)
    path = jobs_dir() / f"{safe_name}.json"
    _write_json_file(path, payload)
    return path


def delete_job(name: str) -> None:
    safe_name = validate_item_name(name)
    path = jobs_dir() / f"{safe_name}.json"
    if not path.exists():
        raise FileNotFoundError(path)
    path.unlink()


def read_job_export(name: str) -> dict[str, Any]:
    safe_name = validate_item_name(name)
    return _read_json_file(job_exports_dir() / f"{safe_name}.json")


def write_job_export(name: str, payload: dict[str, Any]) -> Path:
    safe_name = validate_item_name(name)
    path = job_exports_dir() / f"{safe_name}.json"
    _write_json_file(path, payload)
    return path


def delete_job_export(name: str) -> None:
    safe_name = validate_item_name(name)
    path = job_exports_dir() / f"{safe_name}.json"
    if not path.exists():
        raise FileNotFoundError(path)
    path.unlink()


def read_preset(name: str) -> dict[str, Any]:
    safe_name = validate_item_name(name)
    preset_path = presets_dir() / f"{safe_name}.json"
    control_path = presets_dir() / f"{safe_name}_ctl.json"
    return {
        "name": safe_name,
        "parameters": _read_json_file(preset_path) if preset_path.is_file() else {},
        "control": _read_json_file(control_path) if control_path.is_file() else {},
        "path": str(preset_path),
        "controlPath": str(control_path),
    }


def write_preset(name: str, parameters: dict[str, Any], control: dict[str, Any]) -> dict[str, Path]:
    safe_name = validate_item_name(name)
    preset_path = presets_dir() / f"{safe_name}.json"
    control_path = presets_dir() / f"{safe_name}_ctl.json"
    _write_json_file(preset_path, parameters)
    _write_json_file(control_path, control)
    return {"preset": preset_path, "control": control_path}


def delete_preset(name: str) -> None:
    safe_name = validate_item_name(name)
    preset_path = presets_dir() / f"{safe_name}.json"
    control_path = presets_dir() / f"{safe_name}_ctl.json"
    removed_any = False
    for path in (preset_path, control_path):
        if path.exists():
            path.unlink()
            removed_any = True
    if not removed_any:
        raise FileNotFoundError(preset_path)


def read_last_workspace() -> dict[str, Any]:
    path = last_workspace_path()
    if not path.is_file():
        return {}
    return _read_json_file(path)


def write_last_workspace(payload: dict[str, Any]) -> Path:
    path = last_workspace_path()
    _write_json_file(path, payload)
    return path


def summarize_workspace() -> dict[str, Any]:
    path = last_workspace_path()
    if not path.is_file():
        return {
            "exists": False,
            "path": str(path),
        }
    payload = _read_json_file(path)
    summary = _json_summary(path, "last_workspace", payload)
    summary["exists"] = True
    return summary


def project_data_summary() -> dict[str, Any]:
    return {
        "jobs": len(list_jobs()),
        "jobExports": len(list_job_exports()),
        "presets": len(list_presets()),
        "lastWorkspace": summarize_workspace(),
    }


def relative_project_path(path: Path) -> str:
    try:
        return os.fspath(path.relative_to(project_path()))
    except ValueError:
        return str(path)
