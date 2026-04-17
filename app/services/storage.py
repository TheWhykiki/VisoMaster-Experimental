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


def embeddings_dir() -> Path:
    return ensure_project_dir("embeddings")


def last_workspace_path() -> Path:
    return project_path("last_workspace.json")


def validate_item_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Der Name darf nicht leer sein.")
    if not VALID_NAME_RE.match(cleaned):
        raise ValueError(
            "Der Name enthält ungültige Zeichen. Erlaubt sind nur Buchstaben, Zahlen, Leerzeichen, Bindestriche und Unterstriche."
        )
    return cleaned


def _read_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json_file(path: Path, payload: Any) -> None:
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


def _embedding_summary(path: Path, name: str, payload: Any) -> dict[str, Any]:
    stat = path.stat()
    if not isinstance(payload, list):
        raise ValueError("Embedding-Datei muss eine JSON-Liste sein.")

    entry_count = 0
    model_count = 0
    dimensions: list[int] = []

    for item in payload:
        if not isinstance(item, dict):
            continue
        entry_count += 1
        embedding_store = item.get("embedding_store", {})
        if not isinstance(embedding_store, dict):
            continue
        model_count += len(embedding_store)
        for vector in embedding_store.values():
            if isinstance(vector, list):
                dimensions.append(len(vector))

    return {
        "name": name,
        "path": str(path),
        "size": stat.st_size,
        "modifiedAt": _to_iso(stat.st_mtime),
        "entryCount": entry_count,
        "modelCount": model_count,
        "dimensions": sorted(set(dimensions)),
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


def list_embeddings() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(embeddings_dir().glob("*.json")):
        try:
            payload = _read_json_file(path)
            items.append(_embedding_summary(path, path.stem, payload))
        except (OSError, json.JSONDecodeError, ValueError):
            items.append(
                {
                    "name": path.stem,
                    "path": str(path),
                    "invalid": True,
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


def _normalize_embedding_vector(vector: Any) -> list[float]:
    if not isinstance(vector, list) or not vector:
        raise ValueError("Ein Embedding-Vektor muss eine nicht-leere Liste sein.")

    normalized: list[float] = []
    for value in vector:
        if not isinstance(value, (int, float)):
            raise ValueError("Embedding-Werte muessen numerisch sein.")
        normalized.append(float(value))
    return normalized


def validate_embeddings_payload(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list) or not payload:
        raise ValueError("Embeddings muessen als nicht-leere JSON-Liste gespeichert werden.")

    normalized_entries: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Jeder Embedding-Eintrag muss ein JSON-Objekt sein.")

        name = item.get("name")
        embedding_store = item.get("embedding_store")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Jeder Embedding-Eintrag braucht einen Namen.")
        if not isinstance(embedding_store, dict) or not embedding_store:
            raise ValueError(
                "Jeder Embedding-Eintrag braucht ein nicht-leeres embedding_store-Objekt."
            )

        normalized_store: dict[str, list[float]] = {}
        for model_name, vector in embedding_store.items():
            if not isinstance(model_name, str) or not model_name.strip():
                raise ValueError("Jeder Embedding-Modelname muss ein Textwert sein.")
            normalized_store[model_name.strip()] = _normalize_embedding_vector(vector)

        normalized_entries.append(
            {
                "name": name.strip(),
                "embedding_store": normalized_store,
            }
        )

    return normalized_entries


def read_embedding(name: str) -> list[dict[str, Any]]:
    safe_name = validate_item_name(name)
    payload = _read_json_file(embeddings_dir() / f"{safe_name}.json")
    return validate_embeddings_payload(payload)


def write_embedding(name: str, payload: Any) -> Path:
    safe_name = validate_item_name(name)
    normalized_payload = validate_embeddings_payload(payload)
    path = embeddings_dir() / f"{safe_name}.json"
    _write_json_file(path, normalized_payload)
    return path


def delete_embedding(name: str) -> None:
    safe_name = validate_item_name(name)
    path = embeddings_dir() / f"{safe_name}.json"
    if not path.exists():
        raise FileNotFoundError(path)
    path.unlink()


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
        "embeddings": len(list_embeddings()),
        "lastWorkspace": summarize_workspace(),
    }


def relative_project_path(path: Path) -> str:
    try:
        return os.fspath(path.relative_to(project_path()))
    except ValueError:
        return str(path)
