from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.helpers.paths import ensure_project_dir
from app.services import web_workbench


WORKFLOW_ROOT = ensure_project_dir(".web", "workflow")
TARGET_DIR = ensure_project_dir(".web", "workflow", "target")
SOURCE_DIR = ensure_project_dir(".web", "workflow", "sources")
PREVIEW_DIR = ensure_project_dir(".web", "workflow", "preview")
OUTPUT_DIR = ensure_project_dir(".web", "outputs")
PREVIEW_META_PATH = PREVIEW_DIR / "target_frame.json"
_CV2 = None
_CV2_LOADED = False


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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    temp_path.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def _load_cv2():
    global _CV2, _CV2_LOADED
    if not _CV2_LOADED:
        try:
            import cv2 as imported_cv2
        except ModuleNotFoundError:
            imported_cv2 = None
        _CV2 = imported_cv2
        _CV2_LOADED = True
    return _CV2


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


def _target_file() -> Path | None:
    if not TARGET_DIR.exists():
        return None
    files = [path for path in sorted(TARGET_DIR.iterdir()) if path.is_file()]
    return files[0] if files else None


def _source_file(name: str) -> Path:
    sanitized = _sanitize_filename(name)
    candidate = SOURCE_DIR / sanitized
    if not candidate.is_file():
        raise FileNotFoundError(f"Quellgesicht {sanitized} wurde nicht gefunden.")
    return candidate


def _image_metadata(path: Path) -> dict[str, Any]:
    cv2 = _load_cv2()
    if cv2 is None:
        return {}
    image = cv2.imread(str(path))
    if image is None:
        return {}
    height, width = image.shape[:2]
    return {
        "width": int(width),
        "height": int(height),
    }


def _video_metadata(path: Path) -> dict[str, Any]:
    cv2 = _load_cv2()
    if cv2 is None:
        return {}
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            return {}
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = max(0, int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        payload: dict[str, Any] = {
            "width": width,
            "height": height,
            "fps": round(fps, 3) if fps > 0 else 0,
            "frameCount": frame_count,
            "frameMax": max(0, frame_count - 1),
        }
        if fps > 0 and frame_count > 0:
            payload["durationSeconds"] = round(frame_count / fps, 3)
        return payload
    finally:
        capture.release()


def _media_metadata(path: Path) -> dict[str, Any]:
    file_type = _file_type(path)
    if file_type == "image":
        return _image_metadata(path)
    if file_type == "video":
        return _video_metadata(path)
    return {}


def _preview_state() -> dict[str, Any] | None:
    payload = _read_json(PREVIEW_META_PATH)
    asset_name = str(payload.get("assetName", "")).strip()
    if not asset_name:
        return None
    asset_path = PREVIEW_DIR / asset_name
    if not asset_path.is_file():
        return None
    payload["url"] = f"/api/browser-workflow/preview/frame?ts={int(asset_path.stat().st_mtime)}"
    payload["path"] = str(asset_path)
    return payload


def _entry(path: Path) -> dict[str, Any]:
    stat = path.stat()
    file_type = _file_type(path)
    payload = {
        "name": path.name,
        "path": str(path),
        "size": stat.st_size,
        "modifiedAt": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "fileType": file_type,
    }
    payload.update(_media_metadata(path))
    if path.parent == TARGET_DIR:
        payload["mediaUrl"] = f"/api/browser-workflow/media/target?ts={int(stat.st_mtime)}"
    elif path.parent == SOURCE_DIR:
        payload["mediaUrl"] = (
            f"/api/browser-workflow/media/sources/{path.name}?ts={int(stat.st_mtime)}"
        )
    return payload


def target_media_path() -> Path:
    target = _target_file()
    if target is None:
        raise FileNotFoundError("Es wurde noch kein Zielmedium hochgeladen.")
    return target


def source_media_path(name: str) -> Path:
    return _source_file(name)


def preview_image_path() -> Path:
    preview = _preview_state()
    if not preview:
        raise FileNotFoundError("Es liegt noch keine Ziel-Frame-Vorschau vor.")
    return Path(preview["path"])


def _extract_video_frame(path: Path, frame_index: int) -> tuple[Any, int]:
    cv2 = _load_cv2()
    if cv2 is None:
        raise ValueError(
            "Die Video-Frame-Vorschau braucht OpenCV im aktiven Python-Environment."
        )
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise ValueError("Das Video konnte fuer die Vorschau nicht geoeffnet werden.")
        frame_count = max(0, int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0))
        if frame_count <= 0:
            frame_index = 0
        else:
            frame_index = max(0, min(int(frame_index), frame_count - 1))
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok or frame is None:
            raise ValueError("Der ausgewaehlte Videoframe konnte nicht gelesen werden.")
        return frame, frame_index
    finally:
        capture.release()


def generate_target_preview(frame_index: int = 0) -> dict[str, Any]:
    target = target_media_path()
    file_type = _file_type(target)
    preview_asset_path: Path

    if file_type == "video":
        cv2 = _load_cv2()
        if cv2 is None:
            raise ValueError(
                "Die Video-Frame-Vorschau braucht OpenCV im aktiven Python-Environment."
            )
        frame, normalized_frame = _extract_video_frame(target, frame_index)
        preview_asset_path = PREVIEW_DIR / "target_frame.jpg"
    elif file_type == "image":
        normalized_frame = 0
        preview_asset_path = PREVIEW_DIR / f"target_frame{target.suffix.lower() or '.png'}"
    else:
        raise ValueError("Nur Bilder und Videos koennen als Zielmedium verwendet werden.")

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    for child in PREVIEW_DIR.iterdir():
        if child.name != PREVIEW_META_PATH.name:
            child.unlink()
    if file_type == "video":
        if not cv2.imwrite(str(preview_asset_path), frame):
            raise ValueError("Die Frame-Vorschau konnte nicht gespeichert werden.")
    else:
        shutil.copyfile(target, preview_asset_path)

    metadata = {
        "assetName": preview_asset_path.name,
        "frameIndex": int(normalized_frame),
        "fileType": file_type,
        "targetName": target.name,
        "updatedAt": _iso_now(),
    }
    _write_json(PREVIEW_META_PATH, metadata)
    preview = _preview_state()
    if preview is None:
        raise ValueError("Die Frame-Vorschau konnte nicht gelesen werden.")
    return preview


def current_state() -> dict[str, Any]:
    target_files = sorted(TARGET_DIR.iterdir()) if TARGET_DIR.exists() else []
    source_files = sorted(SOURCE_DIR.iterdir()) if SOURCE_DIR.exists() else []
    target = _entry(target_files[0]) if target_files else None
    sources = [_entry(path) for path in source_files if path.is_file()]
    workbench_state = web_workbench.read_state()
    return {
        "targetMedia": target,
        "sourceFaces": sources,
        "outputFolder": workbench_state["control"]["OutputMediaFolder"],
        "canRun": bool(target and sources),
        "readyMessage": (
            "Direktlauf bereit."
            if target and sources
            else "Bitte Zielmedium und mindestens ein Quellgesicht hochladen."
        ),
        "updatedAt": _iso_now(),
        "assignStrategy": "first_source_to_all_targets",
        "previewFrame": _preview_state(),
        "workbench": workbench_state,
    }


def reset() -> dict[str, Any]:
    _clear_dir(TARGET_DIR)
    _clear_dir(SOURCE_DIR)
    _clear_dir(PREVIEW_DIR)
    return current_state()


def save_target_upload(filename: str, content: bytes) -> dict[str, Any]:
    if not content:
        raise ValueError("Die Ziel-Datei ist leer.")
    _clear_dir(TARGET_DIR)
    _clear_dir(PREVIEW_DIR)
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


def build_run_request(
    detection_frame: int = 0,
    workbench_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = current_state()
    if not state["targetMedia"] or not state["sourceFaces"]:
        raise ValueError("Bitte zuerst Zielmedium und mindestens ein Quellgesicht hochladen.")

    normalized_detection_frame = max(0, int(detection_frame))
    normalized_workbench = web_workbench.normalize_state(
        workbench_state or state.get("workbench")
    )
    return {
        "mode": "upload",
        "label": "Browser-Direktlauf",
        "targetMediaPath": state["targetMedia"]["path"],
        "inputFacePaths": [entry["path"] for entry in state["sourceFaces"]],
        "outputFolder": normalized_workbench["control"]["OutputMediaFolder"],
        "detectionFrame": normalized_detection_frame,
        "assignStrategy": state["assignStrategy"],
        "workbench": normalized_workbench,
    }
