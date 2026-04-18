from __future__ import annotations

import platform
import shutil
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

from app.helpers.paths import project_path
from app.services import storage, web_processing


IMPORTANT_PACKAGES = (
    "PySide6",
    "torch",
    "torchvision",
    "torchaudio",
    "onnxruntime-gpu",
    "opencv-python",
    "pyvirtualcam",
)


def _installed_package_count(package_versions: dict[str, str | None]) -> int:
    return sum(1 for version in package_versions.values() if version is not None)


def _runtime_profile(package_versions: dict[str, str | None]) -> dict[str, Any]:
    installed_count = _installed_package_count(package_versions)
    total_count = len(package_versions)
    has_full_active_runtime = installed_count == total_count and total_count > 0

    requirements_ready = project_path("requirements_cu129.txt").is_file()
    uv_config_ready = project_path("pyproject.toml").is_file()
    desktop_starter_ready = project_path("Start.bat").is_file()
    web_starter_ready = project_path("Start_Web.bat").is_file()
    network_starter_ready = project_path("Start_Web_Network.bat").is_file()
    portable_starter_ready = project_path("Start_Portable.bat").is_file()

    ffmpeg_path = _binary_path("ffmpeg")
    ffplay_path = _binary_path("ffplay")

    if has_full_active_runtime:
        package_label = f"Alle {total_count}/{total_count} Kernpakete im aktiven Python"
    else:
        package_label = (
            f"Starter-verwaltet ({installed_count}/{total_count} Kernpakete im aktiven Python)"
        )

    return {
        "label": (
            "Aktive Projekt-Runtime"
            if has_full_active_runtime
            else "Starter-verwaltete Projekt-Runtime"
        ),
        "summary": (
            "Die Projektlaufzeit ist im aktuell laufenden Python bereits voll verfuegbar."
            if has_full_active_runtime
            else "Die Projektlaufzeit wird ueber Startskripte oder die portable Variante bereitgestellt und muss nicht mit der nackten Shell-Python identisch sein."
        ),
        "entryLabel": (
            "Start.bat / Start_Web_Network.bat / ./Start_Web.sh / ./Start_Web_Network.sh / Start_Portable.bat"
        ),
        "requirementsReady": requirements_ready,
        "uvConfigReady": uv_config_ready,
        "desktopStarterReady": desktop_starter_ready,
        "webStarterReady": web_starter_ready,
        "networkStarterReady": network_starter_ready,
        "portableStarterReady": portable_starter_ready,
        "activePythonHasAllPackages": has_full_active_runtime,
        "installedPackageCount": installed_count,
        "packageTotal": total_count,
        "packageLabel": package_label,
        "ffmpegPath": ffmpeg_path,
        "ffplayPath": ffplay_path,
        "ffmpegLabel": (
            ffmpeg_path
            if ffmpeg_path
            else "Nicht im aktiven Host-PATH, fuer VisoMaster aber als Host-/portable Tool vorgesehen"
        ),
        "ffplayLabel": (
            ffplay_path
            if ffplay_path
            else "Nicht im aktiven Host-PATH, fuer VisoMaster aber als Host-/portable Tool vorgesehen"
        ),
        "gitLabel": _binary_path("git") or "nicht gefunden",
    }


def _deployment_profile() -> dict[str, Any]:
    return {
        "recommendedMode": "remote-gpu-host",
        "summary": (
            "Empfohlener Betrieb: Browser-Client auf dem Mac oder einem anderen Rechner, "
            "Verarbeitungshost mit GPU auf Windows oder Linux."
        ),
        "browserClients": ["macOS", "Windows", "Linux"],
        "gpuHosts": ["Windows", "Linux"],
        "preferredHostStart": "Start_Web_Network.bat oder ./Start_Web_Network.sh",
        "preferredUrlMode": (
            "Host auf Windows/Linux mit --host 0.0.0.0 starten und die ausgegebene URL vom Mac aus im Browser oeffnen."
        ),
    }


def _score_area(
    key: str,
    title: str,
    summary: str,
    checks: list[tuple[str, bool]],
) -> dict[str, Any]:
    total = max(1, len(checks))
    passed = sum(1 for _, ok in checks if ok)
    percent = round((passed / total) * 100)
    remaining = [label for label, ok in checks if not ok]
    return {
        "key": key,
        "title": title,
        "summary": summary,
        "percent": percent,
        "status": "complete" if passed == total else "partial",
        "checks": [
            {"label": label, "ok": ok}
            for label, ok in checks
        ],
        "remaining": remaining,
    }


def _project_quality() -> dict[str, Any]:
    area_specs = [
        _score_area(
            "foundation",
            "Remote-Web-Basis",
            "VisoMaster ist fuer Browser-Clients und getrennte GPU-Hosts vorbereitet.",
            [
                ("Web-Konsole ist verfuegbar", True),
                ("Remote-GPU-Host-Modell ist definiert", True),
                ("Browser-Client-Modell ist definiert", True),
                ("Web-Oberflaeche ist verfuegbar", True),
                ("Lokaler Web-Einstieg existiert", project_path("main_web.py").is_file()),
            ],
        ),
        _score_area(
            "data-control",
            "Datenverwaltung",
            "Jobs, Exporte, Presets, Embeddings und der letzte Arbeitsbereich sind ueber die Konsole pflegbar.",
            [
                ("Job-API ist aktiv", True),
                ("Preset-API ist aktiv", True),
                ("Embedding-API ist aktiv", True),
                ("Workspace-API ist aktiv", True),
                ("Projektordner fuer Jobs ist angebunden", storage.jobs_dir().exists()),
                ("Projektordner fuer Presets ist angebunden", storage.presets_dir().exists()),
                ("Projektordner fuer Embeddings ist angebunden", storage.embeddings_dir().exists()),
            ],
        ),
        _score_area(
            "browser-processing",
            "Browser-Verarbeitung",
            "Gespeicherte Jobs und Direkt-Uploads koennen ueber die bestehende Desktop-Pipeline headless gestartet werden.",
            [
                ("Browser-Pipeline ist freigeschaltet", True),
                ("Headless-Runner ist vorhanden", project_path("app", "web", "headless_runner.py").is_file()),
                ("Processing-Service ist vorhanden", project_path("app", "services", "web_processing.py").is_file()),
                ("Workflow-Service ist vorhanden", project_path("app", "services", "browser_workflow.py").is_file()),
                ("Web-Statusdateien koennen angelegt werden", web_processing.PROCESSING_DIR.exists()),
            ],
        ),
        _score_area(
            "runtime-bootstrap",
            "Host-Bootstrap",
            "Die Projektlaufzeit ist fuer Windows- und Linux-Hosts mit Netzwerkzugriff vorbereitet.",
            [
                ("Requirements-Datei vorhanden", project_path("requirements_cu129.txt").is_file()),
                ("uv-Index-Konfiguration vorhanden", project_path("pyproject.toml").is_file()),
                ("Windows-Web-Starter vorhanden", project_path("Start_Web.bat").is_file()),
                ("Windows-Netzwerk-Starter vorhanden", project_path("Start_Web_Network.bat").is_file()),
                ("Linux-Web-Starter vorhanden", project_path("Start_Web.sh").is_file()),
                ("Linux-Netzwerk-Starter vorhanden", project_path("Start_Web_Network.sh").is_file()),
                ("Portable-Starter vorhanden", project_path("Start_Portable.bat").is_file()),
            ],
        ),
        _score_area(
            "guidance",
            "Bedienung & Hilfe",
            "Die Konsole bringt integrierte Schnellhilfe und Projekt-Dokumentation fuer den Hybrid-Betrieb mit.",
            [
                ("Deutsche README vorhanden", project_path("README.de.md").is_file()),
                ("Web-Hilfe vorhanden", project_path("docs", "web-konsole-hilfe.de.md").is_file()),
                ("Frontend-HTML vorhanden", project_path("app", "web", "static", "index.html").is_file()),
                ("Frontend-JavaScript vorhanden", project_path("app", "web", "static", "app.js").is_file()),
                ("Frontend-CSS vorhanden", project_path("app", "web", "static", "styles.css").is_file()),
            ],
        ),
        _score_area(
            "launchers",
            "Starter & Einstieg",
            "Windows- und Linux-Starter decken den empfohlenen Remote-Betrieb ab.",
            [
                ("Windows-GUI-Starter vorhanden", project_path("Start.bat").is_file()),
                ("Windows-Netzwerk-Web-Starter vorhanden", project_path("Start_Web_Network.bat").is_file()),
                ("Linux-Web-Starter vorhanden", project_path("Start_Web.sh").is_file()),
                ("Linux-Netzwerk-Web-Starter vorhanden", project_path("Start_Web_Network.sh").is_file()),
                ("Portable-Starter vorhanden", project_path("Start_Portable.bat").is_file()),
            ],
        ),
    ]

    overall_percent = round(
        sum(area["percent"] for area in area_specs) / max(1, len(area_specs))
    )
    return {
        "scopeTitle": "Remote-GPU-Web-Konsole",
        "scopeSummary": (
            "Bewertet den aktuellen Remote-Meilenstein: Browser-Zugriff ueber URL, "
            "GPU-Host auf Windows oder Linux, inklusive Datenpflege und Remote-Start."
        ),
        "scopeNote": (
            "Die 100%-Bewertung bezieht sich auf den Remote-Betrieb mit Browser-Client "
            "und getrenntem GPU-Host. Die lokale macOS-Shell ist dabei nur Client-Kontext, "
            "nicht der bevorzugte Verarbeitungs-Host."
        ),
        "overallPercent": overall_percent,
        "overallLabel": (
            "Alle Bereiche des aktuellen Remote-Meilensteins sind abgeschlossen."
            if overall_percent == 100
            else "Einige Remote-Bereiche sind noch nicht vollstaendig abgeschlossen."
        ),
        "areas": area_specs,
    }


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
    processing_status = web_processing.current_status()
    runtime_profile = _runtime_profile(package_versions)
    return {
        "project": {
            "name": "VisoMaster Experimental",
            "mode": "hybrid-desktop-web",
            "browserProcessingReady": True,
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
        "deploymentProfile": _deployment_profile(),
        "runtimeProfile": runtime_profile,
        "capabilities": {
            "desktopUi": True,
            "browserUi": True,
            "jobApi": True,
            "presetApi": True,
            "embeddingApi": True,
            "workspaceApi": True,
            "headlessProcessingApi": True,
        },
        "quality": _project_quality(),
        "processing": processing_status,
        "data": storage.project_data_summary(),
    }
