from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.helpers.paths import ensure_project_dir


WORKFLOW_ROOT = ensure_project_dir(".web", "workflow")
TARGET_DIR = ensure_project_dir(".web", "workflow", "target")
SOURCE_DIR = ensure_project_dir(".web", "workflow", "sources")
OUTPUT_DIR = ensure_project_dir(".web", "outputs")


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_filename(name: str) -> str:
    candidate = Path(name or "").name.strip()
    if not candidate:
        raise ValueError("Der Dateiname fehlt.")
    return candidate.replace("/", "_").replace("\\", "_")


def _clear_dir(path: Path) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _unique_path(base_dir: Path, filename: str) -> Path:
    target = base_dir / filename
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    index = 2
    while True:
        candidate = base_dir / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def _file_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    return "unknown"


def _entry(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path),
        "size": stat.st_size,
        "modifiedAt": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "fileType": _file_type(path),
    }


def current_state() -> dict[str, Any]:
    target_files = sorted(TARGET_DIR.iterdir()) if TARGET_DIR.exists() else []
    source_files = sorted(SOURCE_DIR.iterdir()) if SOURCE_DIR.exists() else []
    target = _entry(target_files[0]) if target_files else None
    sources = [_entry(path) for path in source_files if path.is_file()]
    return {
        "targetMedia": target,
        "sourceFaces": sources,
        "outputFolder": str(OUTPUT_DIR),
        "canRun": bool(target and sources),
        "readyMessage": (
            "Direktlauf bereit."
            if target and sources
            else "Bitte Zielmedium und mindestens ein Quellgesicht hochladen."
        ),
        "updatedAt": _iso_now(),
        "assignStrategy": "first_source_to_all_targets",
    }


def reset() -> dict[str, Any]:
    _clear_dir(TARGET_DIR)
    _clear_dir(SOURCE_DIR)
    return current_state()


def save_target_upload(filename: str, content: bytes) -> dict[str, Any]:
    if not content:
        raise ValueError("Die Ziel-Datei ist leer.")
    _clear_dir(TARGET_DIR)
    sanitized = _sanitize_filename(filename)
    path = TARGET_DIR / sanitized
    path.write_bytes(content)
    return {"saved": _entry(path), "state": current_state()}


def save_source_uploads(files: list[tuple[str, bytes]]) -> dict[str, Any]:
    if not files:
        raise ValueError("Es wurden keine Quellbilder hochgeladen.")

    _clear_dir(SOURCE_DIR)
    saved_items: list[dict[str, Any]] = []
    for filename, content in files:
        if not content:
            continue
        sanitized = _sanitize_filename(filename)
        path = _unique_path(SOURCE_DIR, sanitized)
        path.write_bytes(content)
        saved_items.append(_entry(path))

    if not saved_items:
        raise ValueError("Die hochgeladenen Quellbilder waren leer.")

    return {"saved": saved_items, "state": current_state()}


def build_run_request(detection_frame: int = 0) -> dict[str, Any]:
    state = current_state()
    if not state["targetMedia"] or not state["sourceFaces"]:
        raise ValueError("Bitte zuerst Zielmedium und mindestens ein Quellgesicht hochladen.")

    normalized_detection_frame = max(0, int(detection_frame))
    return {
        "mode": "upload",
        "label": "Browser-Direktlauf",
        "targetMediaPath": state["targetMedia"]["path"],
        "inputFacePaths": [entry["path"] for entry in state["sourceFaces"]],
        "outputFolder": str(OUTPUT_DIR),
        "detectionFrame": normalized_detection_frame,
        "assignStrategy": state["assignStrategy"],
    }
