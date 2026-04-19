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
TARGET_PREVIEW_META_PATH = PREVIEW_DIR / "target_frame.json"
SWAP_PREVIEW_META_PATH = PREVIEW_DIR / "swap_preview.json"
DETECTED_FACES_META_PATH = PREVIEW_DIR / "detected_faces.json"
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
    return _preview_state_from(
        meta_path=TARGET_PREVIEW_META_PATH,
        route="/api/browser-workflow/preview/frame",
    )


def _swap_preview_state() -> dict[str, Any] | None:
    return _preview_state_from(
        meta_path=SWAP_PREVIEW_META_PATH,
        route="/api/browser-workflow/preview/swap",
    )


def _detected_faces_state() -> dict[str, Any] | None:
    payload = _read_json(DETECTED_FACES_META_PATH)
    faces = payload.get("faces")
    if not isinstance(faces, list) or not faces:
        return None

    normalized_faces: list[dict[str, Any]] = []
    for entry in faces:
        if not isinstance(entry, dict):
            continue
        asset_name = str(entry.get("assetName", "")).strip()
        if not asset_name:
            continue
        asset_path = PREVIEW_DIR / asset_name
        if not asset_path.is_file():
            continue
        normalized = dict(entry)
        normalized["path"] = str(asset_path)
        normalized["mediaUrl"] = (
            f"/api/browser-workflow/faces/{asset_name}?ts={int(asset_path.stat().st_mtime)}"
        )
        normalized_faces.append(normalized)

    if not normalized_faces:
        return None

    payload["faces"] = normalized_faces
    return payload


def _preview_state_from(meta_path: Path, route: str) -> dict[str, Any] | None:
    payload = _read_json(meta_path)
    asset_name = str(payload.get("assetName", "")).strip()
    if not asset_name:
        return None
    asset_path = PREVIEW_DIR / asset_name
    if not asset_path.is_file():
        return None
    payload["url"] = f"{route}?ts={int(asset_path.stat().st_mtime)}"
    payload["path"] = str(asset_path)
    return payload


def _workflow_status(
    target: dict[str, Any] | None,
    sources: list[dict[str, Any]],
    preview_frame: dict[str, Any] | None,
    swap_preview: dict[str, Any] | None,
    detected_faces: dict[str, Any] | None,
) -> dict[str, Any]:
    is_video_target = bool(target and target.get("fileType") == "video")
    preview_frame_index = int(preview_frame.get("frameIndex", 0)) if preview_frame else 0
    detected_frame_index = (
        int(detected_faces.get("frameIndex", 0)) if detected_faces else preview_frame_index
    )
    swap_preview_frame_index = (
        int(swap_preview.get("frameIndex", 0)) if swap_preview else preview_frame_index
    )

    has_target = bool(target)
    has_sources = bool(sources)
    has_preview_frame = bool(target and (not is_video_target or preview_frame))
    has_detected_faces = bool(
        detected_faces and int(detected_faces.get("count", 0) or 0) > 0
    )
    has_swap_preview = bool(swap_preview)

    steps = [
        {
            "id": "target",
            "label": "Target laden",
            "ready": has_target,
            "detail": (
                target["name"]
                if has_target
                else "Bitte ein Zielbild oder Zielvideo hochladen."
            ),
        },
        {
            "id": "sources",
            "label": "Source Faces laden",
            "ready": has_sources,
            "detail": (
                f"{len(sources)} Quellgesicht(er) bereit."
                if has_sources
                else "Bitte mindestens ein Quellgesicht hochladen."
            ),
        },
        {
            "id": "frame",
            "label": "Detection Frame bestaetigen",
            "ready": has_preview_frame,
            "detail": (
                f"Frame {preview_frame_index} als Detection-Preview gespeichert."
                if has_preview_frame
                else "Bei Videos zuerst Preview Frame fuer den aktuellen Scrub-Frame erzeugen."
            ),
        },
        {
            "id": "detect",
            "label": "Target Faces finden",
            "ready": has_detected_faces,
            "detail": (
                f"{int(detected_faces.get('count', 0) or 0)} Zielgesicht(er) auf Frame {detected_frame_index} erkannt."
                if has_detected_faces and detected_faces
                else "Noch keine Zielgesichter fuer den aktuellen Detection-Frame gefunden."
            ),
        },
        {
            "id": "preview",
            "label": "Swap Preview pruefen",
            "ready": has_swap_preview,
            "detail": (
                f"Geswappte Vorschau fuer Frame {swap_preview_frame_index} vorhanden."
                if has_swap_preview
                else "Noch keine geswappte Vorschau berechnet."
            ),
        },
    ]

    if not has_target:
        next_action = "Lade zuerst das Zielmedium."
    elif not has_sources:
        next_action = "Lade jetzt mindestens ein Quellgesicht."
    elif not has_preview_frame:
        next_action = "Erzeuge jetzt mit Preview Frame einen bestaetigten Detection-Frame."
    elif not has_detected_faces:
        next_action = "Finde jetzt die Zielgesichter auf dem aktuellen Detection-Frame."
    elif not has_swap_preview:
        next_action = "Erzeuge jetzt eine geswappte Vorschau."
    else:
        next_action = "Alle Schritte sind bereit. Du kannst jetzt den eigentlichen Swap starten."

    return {
        "isVideoTarget": is_video_target,
        "previewFrameIndex": preview_frame_index,
        "detectedFrameIndex": detected_frame_index,
        "swapPreviewFrameIndex": swap_preview_frame_index,
        "canFindFaces": has_target and has_preview_frame,
        "canSwapPreview": has_target and has_sources and has_preview_frame and has_detected_faces,
        "canRun": has_target and has_sources and has_preview_frame and has_detected_faces,
        "nextAction": next_action,
        "steps": steps,
    }


def _clear_preview_asset(meta_path: Path) -> None:
    payload = _read_json(meta_path)
    asset_name = str(payload.get("assetName", "")).strip()
    if asset_name:
        asset_path = PREVIEW_DIR / asset_name
        if asset_path.is_file():
            asset_path.unlink()
    if meta_path.is_file():
        meta_path.unlink()


def _clear_detected_faces() -> None:
    payload = _read_json(DETECTED_FACES_META_PATH)
    faces = payload.get("faces")
    if isinstance(faces, list):
        for entry in faces:
            if not isinstance(entry, dict):
                continue
            asset_name = str(entry.get("assetName", "")).strip()
            if not asset_name:
                continue
            asset_path = PREVIEW_DIR / asset_name
            if asset_path.is_file():
                asset_path.unlink()
    if DETECTED_FACES_META_PATH.is_file():
        DETECTED_FACES_META_PATH.unlink()


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


def detected_face_image_path(name: str) -> Path:
    candidate = (PREVIEW_DIR / Path(name)).resolve()
    preview_root = PREVIEW_DIR.resolve()
    if not str(candidate).startswith(str(preview_root)) or not candidate.is_file():
        raise FileNotFoundError("Das gefundene Zielgesicht wurde nicht gefunden.")
    return candidate


def preview_image_path() -> Path:
    preview = _preview_state()
    if not preview:
        raise FileNotFoundError("Es liegt noch keine Ziel-Frame-Vorschau vor.")
    return Path(preview["path"])


def swap_preview_image_path() -> Path:
    preview = _swap_preview_state()
    if not preview:
        raise FileNotFoundError("Es liegt noch keine geswappte Vorschau vor.")
    return Path(preview["path"])


def swap_preview_output_path() -> Path:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    return PREVIEW_DIR / "swap_preview.png"


def clear_swap_preview() -> None:
    _clear_preview_asset(SWAP_PREVIEW_META_PATH)


def clear_detected_faces() -> None:
    _clear_detected_faces()
    clear_swap_preview()


def register_swap_preview(asset_path: Path, frame_index: int, *, source_count: int) -> dict[str, Any]:
    if not asset_path.is_file():
        raise FileNotFoundError("Die geswappte Vorschau-Datei wurde nicht gefunden.")
    metadata = {
        "assetName": asset_path.name,
        "frameIndex": int(max(0, frame_index)),
        "fileType": _file_type(asset_path),
        "targetName": target_media_path().name,
        "sourceCount": int(max(0, source_count)),
        "updatedAt": _iso_now(),
    }
    _write_json(SWAP_PREVIEW_META_PATH, metadata)
    preview = _swap_preview_state()
    if preview is None:
        raise ValueError("Die geswappte Vorschau konnte nicht registriert werden.")
    return preview


def found_faces_dir() -> Path:
    path = PREVIEW_DIR / "faces"
    path.mkdir(parents=True, exist_ok=True)
    return path


def found_faces_manifest_path() -> Path:
    return PREVIEW_DIR / "faces_manifest.json"


def register_detected_faces(payload: dict[str, Any] | None) -> dict[str, Any]:
    clear_detected_faces()
    if not isinstance(payload, dict):
        raise ValueError("Die Zielgesichter konnten nicht registriert werden.")
    faces = payload.get("faces")
    if not isinstance(faces, list) or not faces:
        raise ValueError("Es wurden keine Zielgesichter erkannt.")

    normalized_faces: list[dict[str, Any]] = []
    for index, entry in enumerate(faces, start=1):
        if not isinstance(entry, dict):
            continue
        asset_name = str(entry.get("assetName", "")).strip()
        if not asset_name:
            continue
        asset_path = PREVIEW_DIR / asset_name
        if not asset_path.is_file():
            continue
        normalized_faces.append(
            {
                "assetName": asset_name,
                "label": str(entry.get("label") or f"Target Face {index}"),
                "faceId": str(entry.get("faceId") or index),
                "frameIndex": int(entry.get("frameIndex", 0) or 0),
                "fileType": "image",
                "targetName": str(entry.get("targetName") or target_media_path().name),
            }
        )

    if not normalized_faces:
        raise ValueError("Es wurden keine gueltigen Zielgesichter registriert.")

    metadata = {
        "frameIndex": int(payload.get("frameIndex", 0) or 0),
        "targetName": str(payload.get("targetName") or target_media_path().name),
        "count": len(normalized_faces),
        "updatedAt": _iso_now(),
        "faces": normalized_faces,
    }
    _write_json(DETECTED_FACES_META_PATH, metadata)
    state = _detected_faces_state()
    if state is None:
        raise ValueError("Die Zielgesichter konnten nicht gelesen werden.")
    return state


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
    clear_detected_faces()
    _clear_preview_asset(TARGET_PREVIEW_META_PATH)
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
    _write_json(TARGET_PREVIEW_META_PATH, metadata)
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
    preview_frame = _preview_state()
    swap_preview = _swap_preview_state()
    detected_faces = _detected_faces_state()
    workflow = _workflow_status(
        target=target,
        sources=sources,
        preview_frame=preview_frame,
        swap_preview=swap_preview,
        detected_faces=detected_faces,
    )
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
        "assignStrategy": workbench_state["control"].get(
            "BrowserAssignStrategySelection",
            "first_source_to_all_targets",
        ),
        "previewFrame": preview_frame,
        "swapPreview": swap_preview,
        "detectedTargetFaces": detected_faces,
        "workflow": workflow,
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
    clear_swap_preview()
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


def build_find_faces_request(
    detection_frame: int = 0,
    workbench_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = current_state()
    if not state["targetMedia"]:
        raise ValueError("Bitte zuerst ein Zielmedium hochladen.")

    normalized_detection_frame = max(0, int(detection_frame))
    normalized_workbench = web_workbench.normalize_state(
        workbench_state or state.get("workbench")
    )
    return {
        "mode": "find_faces",
        "label": "Browser-Face-Detect",
        "targetMediaPath": state["targetMedia"]["path"],
        "foundFacesDir": str(found_faces_dir()),
        "foundFacesManifestPath": str(found_faces_manifest_path()),
        "detectionFrame": normalized_detection_frame,
        "workbench": normalized_workbench,
    }


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
        "assignStrategy": normalized_workbench["control"].get(
            "BrowserAssignStrategySelection",
            state["assignStrategy"],
        ),
        "workbench": normalized_workbench,
    }
