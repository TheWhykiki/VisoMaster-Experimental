from __future__ import annotations

import platform
import shutil
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

from app.services import storage


IMPORTANT_PACKAGES = (
    "PySide6",
    "torch",
    "torchvision",
    "torchaudio",
    "onnxruntime-gpu",
    "opencv-python",
    "pyvirtualcam",
)


def _package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _binary_path(name: str) -> str | None:
    match = shutil.which(name)
    return str(Path(match)) if match else None


def system_status() -> dict[str, Any]:
    package_versions = {
        name: _package_version(name) for name in IMPORTANT_PACKAGES
    }
    return {
        "project": {
            "name": "VisoMaster Experimental",
            "mode": "hybrid-desktop-web",
            "browserProcessingReady": False,
        },
        "runtime": {
            "pythonVersion": sys.version.split()[0],
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
        },
        "binaries": {
            "ffmpeg": _binary_path("ffmpeg"),
            "ffplay": _binary_path("ffplay"),
            "git": _binary_path("git"),
        },
        "packages": package_versions,
        "capabilities": {
            "desktopUi": True,
            "browserUi": True,
            "jobApi": True,
            "presetApi": True,
            "embeddingApi": True,
            "workspaceApi": True,
            "headlessProcessingApi": False,
        },
        "data": storage.project_data_summary(),
    }
