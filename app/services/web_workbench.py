from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from app.helpers.paths import ensure_project_dir
from app.processors.models_data import (
    ACE_LOCAL_AUTO_OPTION,
    ACE_PORTRAIT_AUTO_OPTION,
    ACE_SUBJECT_AUTO_OPTION,
    FLUX_FILL_AUTO_OPTION,
)


WORKBENCH_DIR = ensure_project_dir(".web", "workflow")
WORKBENCH_DRAFT_PATH = WORKBENCH_DIR / "swap_workbench.json"
DEFAULT_OUTPUT_FOLDER = str(ensure_project_dir(".web", "outputs"))


WORKBENCH_TABS: list[dict[str, Any]] = [
    {
        "id": "swap",
        "label": "Face Swap",
        "description": "Modell, Aehnlichkeit und Kernparameter fuer den eigentlichen Swap.",
        "sections": [
            {
                "id": "swap-core",
                "title": "Core Swap",
                "controls": [
                    {
                        "scope": "parameters",
                        "key": "SwapModelSelection",
                        "type": "select",
                        "label": "Swapper Model",
                        "default": "Inswapper128",
                        "options": [
                            "Inswapper128",
                            "InStyleSwapper256 Version A",
                            "InStyleSwapper256 Version B",
                            "InStyleSwapper256 Version C",
                            "DeepFaceLive (DFM)",
                            "SimSwap512",
                            "GhostFace-v1",
                            "GhostFace-v2",
                            "GhostFace-v3",
                            "CSCS",
                            "CanonSwap",
                            "ACE++ (FLUX)",
                        ],
                        "help": "Entspricht dem nativen Swapper-Auswahlfeld der Desktop-App.",
                    },
                    {
                        "scope": "parameters",
                        "key": "SwapperResSelection",
                        "type": "select",
                        "label": "Swapper Resolution",
                        "default": "128",
                        "options": ["128", "256", "384", "512"],
                        "parentSelection": "SwapModelSelection",
                        "requiredSelectionValue": "Inswapper128",
                        "help": "Hoehere Werte liefern mehr Details, kosten aber Zeit und VRAM.",
                    },
                    {
                        "scope": "parameters",
                        "key": "SwapperResAutoSelectEnableToggle",
                        "type": "toggle",
                        "label": "Auto Resolution",
                        "default": False,
                        "parentSelection": "SwapModelSelection",
                        "requiredSelectionValue": "Inswapper128",
                        "help": "Orientiert sich an der Original-Face-Groesse.",
                    },
                    {
                        "scope": "parameters",
                        "key": "SimilarityThresholdSlider",
                        "type": "range",
                        "label": "Similarity Threshold",
                        "default": 60,
                        "min": 1,
                        "max": 100,
                        "step": 1,
                        "help": "Aehnlichkeitsschwelle fuer das Zuweisen und Austauschen von Gesichtern.",
                    },
                    {
                        "scope": "parameters",
                        "key": "PreSwapSharpnessDecimalSlider",
                        "type": "range",
                        "label": "Pre Swap Sharpness",
                        "default": 1.0,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.1,
                        "decimals": 1,
                        "help": "Leichte Schaerfung vor dem eigentlichen Swap.",
                    },
                ],
            },
            {
                "id": "swap-likeness",
                "title": "Strength & Likeness",
                "controls": [
                    {
                        "scope": "parameters",
                        "key": "StrengthEnableToggle",
                        "type": "toggle",
                        "label": "Strength",
                        "default": False,
                        "help": "Mehrfache Swap-Anwendung fuer staerkere Identitaetsuebernahme.",
                    },
                    {
                        "scope": "parameters",
                        "key": "StrengthAmountSlider",
                        "type": "range",
                        "label": "Strength Amount",
                        "default": 100,
                        "min": 0,
                        "max": 500,
                        "step": 25,
                        "parentToggle": "StrengthEnableToggle",
                        "requiredToggleValue": True,
                        "help": "200 ist oft ein guter Startpunkt fuer deutlicheren Likeness-Effekt.",
                    },
                    {
                        "scope": "parameters",
                        "key": "FaceLikenessEnableToggle",
                        "type": "toggle",
                        "label": "Face Likeness",
                        "default": False,
                        "help": "Zusatzregler fuer die Gesichtsnaehe zwischen Quelle und Ziel.",
                    },
                    {
                        "scope": "parameters",
                        "key": "FaceLikenessFactorDecimalSlider",
                        "type": "range",
                        "label": "Likeness Amount",
                        "default": 0.0,
                        "min": -1.0,
                        "max": 1.0,
                        "step": 0.05,
                        "decimals": 2,
                        "parentToggle": "FaceLikenessEnableToggle",
                        "requiredToggleValue": True,
                        "help": "Feinregelung fuer mehr oder weniger Naehe zur Referenzidentitaet.",
                    },
                ],
            },
            {
                "id": "swap-flux",
                "title": "ACE++ / FLUX",
                "controls": [
                    {
                        "scope": "parameters",
                        "key": "FluxModelSelection",
                        "type": "select",
                        "label": "FLUX Base Model",
                        "default": FLUX_FILL_AUTO_OPTION,
                        "options": [FLUX_FILL_AUTO_OPTION],
                        "parentSelection": "SwapModelSelection",
                        "requiredSelectionValue": "ACE++ (FLUX)",
                        "help": "Auto-downloads FLUX.1 Fill [dev]. Local Kontext models remain available in the native app.",
                    },
                    {
                        "scope": "parameters",
                        "key": "FluxLoraSelection",
                        "type": "select",
                        "label": "ACE++ / LoRA",
                        "default": ACE_PORTRAIT_AUTO_OPTION,
                        "options": [
                            ACE_PORTRAIT_AUTO_OPTION,
                            ACE_SUBJECT_AUTO_OPTION,
                            ACE_LOCAL_AUTO_OPTION,
                        ],
                        "parentSelection": "SwapModelSelection",
                        "requiredSelectionValue": "ACE++ (FLUX)",
                        "help": "ACE++ LoRA preset used for the generative face inpaint pass.",
                    },
                    {
                        "scope": "parameters",
                        "key": "FluxSettingsEnableToggle",
                        "type": "toggle",
                        "label": "Show FLUX Settings",
                        "default": False,
                        "parentSelection": "SwapModelSelection",
                        "requiredSelectionValue": "ACE++ (FLUX)",
                        "help": "Aktiviert die erweiterten ACE++-Parameter im Browser.",
                    },
                    {
                        "scope": "parameters",
                        "key": "FluxPromptText",
                        "type": "text",
                        "label": "Prompt",
                        "default": "swap the masked face to the reference identity, preserve expression, pose, skin texture, framing, and scene lighting",
                        "parentSelection": "SwapModelSelection",
                        "requiredSelectionValue": "ACE++ (FLUX)",
                        "parentToggle": "FluxSettingsEnableToggle",
                        "requiredToggleValue": True,
                        "help": "Prompt fuer den ACE++-Swapper.",
                    },
                    {
                        "scope": "parameters",
                        "key": "FluxNegativePromptText",
                        "type": "text",
                        "label": "Negative Prompt",
                        "default": "deformed face, extra eyes, extra mouth, distorted identity, low quality, blurry, waxy skin, bad anatomy",
                        "parentSelection": "SwapModelSelection",
                        "requiredSelectionValue": "ACE++ (FLUX)",
                        "parentToggle": "FluxSettingsEnableToggle",
                        "requiredToggleValue": True,
                        "help": "Negativprompt fuer ACE++ / FLUX.",
                    },
                    {
                        "scope": "parameters",
                        "key": "FluxStepsSlider",
                        "type": "range",
                        "label": "Inference Steps",
                        "default": 20,
                        "min": 4,
                        "max": 60,
                        "step": 1,
                        "parentSelection": "SwapModelSelection",
                        "requiredSelectionValue": "ACE++ (FLUX)",
                        "parentToggle": "FluxSettingsEnableToggle",
                        "requiredToggleValue": True,
                        "help": "Anzahl der Inference-Schritte fuer FLUX.",
                    },
                    {
                        "scope": "parameters",
                        "key": "FluxGuidanceDecimalSlider",
                        "type": "range",
                        "label": "Guidance",
                        "default": 3.5,
                        "min": 0.0,
                        "max": 10.0,
                        "step": 0.1,
                        "decimals": 1,
                        "parentSelection": "SwapModelSelection",
                        "requiredSelectionValue": "ACE++ (FLUX)",
                        "parentToggle": "FluxSettingsEnableToggle",
                        "requiredToggleValue": True,
                        "help": "Guidance-Scale fuer den ACE++-Lauf.",
                    },
                    {
                        "scope": "parameters",
                        "key": "FluxLoRAStrengthDecimalSlider",
                        "type": "range",
                        "label": "LoRA Strength",
                        "default": 1.0,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.05,
                        "decimals": 2,
                        "parentSelection": "SwapModelSelection",
                        "requiredSelectionValue": "ACE++ (FLUX)",
                        "parentToggle": "FluxSettingsEnableToggle",
                        "requiredToggleValue": True,
                        "help": "Mischstaerke des gewaehlten ACE++ LoRA.",
                    },
                    {
                        "scope": "parameters",
                        "key": "FluxSeedSlider",
                        "type": "range",
                        "label": "Seed",
                        "default": 0,
                        "min": 0,
                        "max": 999999,
                        "step": 1,
                        "parentSelection": "SwapModelSelection",
                        "requiredSelectionValue": "ACE++ (FLUX)",
                        "parentToggle": "FluxSettingsEnableToggle",
                        "requiredToggleValue": True,
                        "help": "0 erzeugt pro Lauf einen zufaelligen Seed.",
                    },
                    {
                        "scope": "parameters",
                        "key": "FluxUseSourceReferenceToggle",
                        "type": "toggle",
                        "label": "Use Source Reference",
                        "default": False,
                        "parentSelection": "SwapModelSelection",
                        "requiredSelectionValue": "ACE++ (FLUX)",
                        "parentToggle": "FluxSettingsEnableToggle",
                        "requiredToggleValue": True,
                        "help": "Nur fuer lokale FLUX Kontext Inpaint-Modelle aktivieren. FLUX.1 Fill nutzt keine direkte Source-Reference.",
                    },
                    {
                        "scope": "parameters",
                        "key": "FluxCPUOffloadToggle",
                        "type": "toggle",
                        "label": "CPU Offload",
                        "default": True,
                        "parentSelection": "SwapModelSelection",
                        "requiredSelectionValue": "ACE++ (FLUX)",
                        "parentToggle": "FluxSettingsEnableToggle",
                        "requiredToggleValue": True,
                        "help": "Reduziert VRAM-Verbrauch auf dem GPU-Host.",
                    },
                ],
            },
        ],
    },
    {
        "id": "restoration",
        "label": "Face Tools",
        "description": "Restorer- und Blend-Werkzeuge wie in den nativen Nebenreitern.",
        "sections": [
            {
                "id": "restorer-main",
                "title": "Face Restorer",
                "controls": [
                    {
                        "scope": "parameters",
                        "key": "FaceRestorerEnableToggle",
                        "type": "toggle",
                        "label": "Enable Face Restorer",
                        "default": False,
                        "help": "Aktiviert den ersten Face-Restorer.",
                    },
                    {
                        "scope": "parameters",
                        "key": "FaceRestorerTypeSelection",
                        "type": "select",
                        "label": "Restorer Type",
                        "default": "GFPGAN-v1.4",
                        "options": [
                            "GFPGAN-v1.4",
                            "GFPGAN-1024",
                            "CodeFormer",
                            "GPEN-256",
                            "GPEN-512",
                            "GPEN-1024",
                            "RestoreFormer++",
                            "VQFR-v2",
                        ],
                        "parentToggle": "FaceRestorerEnableToggle",
                        "requiredToggleValue": True,
                        "help": "Wahl des nativen Restorer-Modells.",
                    },
                    {
                        "scope": "parameters",
                        "key": "FaceRestorerBlendSlider",
                        "type": "range",
                        "label": "Restorer Blend",
                        "default": 100,
                        "min": 0,
                        "max": 100,
                        "step": 1,
                        "parentToggle": "FaceRestorerEnableToggle",
                        "requiredToggleValue": True,
                        "help": "Mischt restaurierte und geswappte Flaeche.",
                    },
                    {
                        "scope": "parameters",
                        "key": "FaceRestorerAutoEnableToggle",
                        "type": "toggle",
                        "label": "Auto Restore",
                        "default": False,
                        "parentToggle": "FaceRestorerEnableToggle",
                        "requiredToggleValue": True,
                        "help": "Laesst den Blend-Wert automatisch schaerfeabhaengig regeln.",
                    },
                ],
            },
            {
                "id": "restorer-secondary",
                "title": "Secondary Pass",
                "controls": [
                    {
                        "scope": "parameters",
                        "key": "FaceRestorerEnable2Toggle",
                        "type": "toggle",
                        "label": "Enable Face Restorer 2",
                        "default": False,
                        "help": "Zweiter Restorer-Durchlauf fuer spaete Korrekturen.",
                    },
                    {
                        "scope": "parameters",
                        "key": "FaceRestorerEnable2EndToggle",
                        "type": "toggle",
                        "label": "Apply at End",
                        "default": False,
                        "parentToggle": "FaceRestorerEnable2Toggle",
                        "requiredToggleValue": True,
                        "help": "Zweiten Restorer ans Ende der Pipeline verschieben.",
                    },
                    {
                        "scope": "parameters",
                        "key": "FaceRestorerType2Selection",
                        "type": "select",
                        "label": "Restorer 2 Type",
                        "default": "GFPGAN-v1.4",
                        "options": [
                            "GFPGAN-v1.4",
                            "GFPGAN-1024",
                            "CodeFormer",
                            "GPEN-256",
                            "GPEN-512",
                            "GPEN-1024",
                            "RestoreFormer++",
                            "VQFR-v2",
                        ],
                        "parentToggle": "FaceRestorerEnable2Toggle",
                        "requiredToggleValue": True,
                        "help": "Modell fuer den zweiten Restorer-Durchlauf.",
                    },
                    {
                        "scope": "parameters",
                        "key": "FaceRestorerBlend2Slider",
                        "type": "range",
                        "label": "Restorer 2 Blend",
                        "default": 100,
                        "min": 0,
                        "max": 100,
                        "step": 1,
                        "parentToggle": "FaceRestorerEnable2Toggle",
                        "requiredToggleValue": True,
                        "help": "Blend-Wert fuer den zweiten Restorer.",
                    },
                ],
            },
        ],
    },
    {
        "id": "detect",
        "label": "Detectors",
        "description": "Erkennung, Zuordnung und Performance-Schrauben fuer den Host.",
        "sections": [
            {
                "id": "detect-core",
                "title": "Face Detection",
                "controls": [
                    {
                        "scope": "control",
                        "key": "RecognitionModelSelection",
                        "type": "select",
                        "label": "Recognition Model",
                        "default": "Inswapper128ArcFace",
                        "options": [
                            "Inswapper128ArcFace",
                            "SimSwapArcFace",
                            "GhostArcFace",
                            "CSCSArcFace",
                            "CanonSwapArcFace",
                        ],
                        "help": "ArcFace-Modell fuer die Gesichtsaehnlichkeit.",
                    },
                    {
                        "scope": "control",
                        "key": "SimilarityTypeSelection",
                        "type": "select",
                        "label": "Similarity Type",
                        "default": "Opal",
                        "options": ["Opal", "Pearl", "Optimal"],
                        "help": "Native Aehnlichkeitsstrategie fuer Matching und Assignment.",
                    },
                    {
                        "scope": "control",
                        "key": "DetectorModelSelection",
                        "type": "select",
                        "label": "Face Detect Model",
                        "default": "RetinaFace",
                        "options": ["RetinaFace", "Yolov8", "SCRFD", "Yunet"],
                        "help": "Detektor fuer Ziel- und Quellgesichter.",
                    },
                    {
                        "scope": "control",
                        "key": "DetectorScoreSlider",
                        "type": "range",
                        "label": "Detect Score",
                        "default": 50,
                        "min": 1,
                        "max": 100,
                        "step": 1,
                        "help": "Hoeher = strengere Erkennung.",
                    },
                    {
                        "scope": "control",
                        "key": "MaxFacesToDetectSlider",
                        "type": "range",
                        "label": "Max Faces",
                        "default": 20,
                        "min": 1,
                        "max": 50,
                        "step": 1,
                        "help": "Maximale Anzahl erkannter Gesichter pro Frame.",
                    },
                    {
                        "scope": "control",
                        "key": "AutoRotationToggle",
                        "type": "toggle",
                        "label": "Auto Rotation",
                        "default": False,
                        "help": "Dreht Erkennungswinkel automatisch mit.",
                    },
                    {
                        "scope": "control",
                        "key": "ManualRotationEnableToggle",
                        "type": "toggle",
                        "label": "Manual Rotation",
                        "default": False,
                        "help": "Fixer Rotationswinkel fuer schwierige Zielmedien.",
                    },
                    {
                        "scope": "control",
                        "key": "ManualRotationAngleSlider",
                        "type": "range",
                        "label": "Rotation Angle",
                        "default": 0,
                        "min": 0,
                        "max": 270,
                        "step": 90,
                        "parentToggle": "ManualRotationEnableToggle",
                        "requiredToggleValue": True,
                        "help": "Clockwise-Rotation fuer den Detektor.",
                    },
                ],
            },
            {
                "id": "detect-runtime",
                "title": "Runtime",
                "controls": [
                    {
                        "scope": "control",
                        "key": "ProvidersPrioritySelection",
                        "type": "select",
                        "label": "Providers Priority",
                        "default": "CUDA",
                        "options": ["CUDA", "TensorRT", "TensorRT-Engine", "CPU"],
                        "help": "Prioritaet der Ausfuehrungsprovider auf dem GPU-Host.",
                    },
                    {
                        "scope": "control",
                        "key": "nThreadsSlider",
                        "type": "range",
                        "label": "Number of Threads",
                        "default": 1,
                        "min": 1,
                        "max": 30,
                        "step": 1,
                        "help": "Mehr Threads fuer mehr Durchsatz, aber auch mehr Last.",
                    },
                    {
                        "scope": "control",
                        "key": "AutoSwapToggle",
                        "type": "toggle",
                        "label": "Auto Swap",
                        "default": False,
                        "help": "Automatische Anwendung bei geladenen Medien.",
                    },
                    {
                        "scope": "control",
                        "key": "SwapOnlyBestMatchEnableToggle",
                        "type": "toggle",
                        "label": "Swap Input Face Only Once",
                        "default": False,
                        "help": "Tauscht nur das beste Match pro Eingabegesicht.",
                    },
                    {
                        "scope": "control",
                        "key": "BrowserAssignStrategySelection",
                        "type": "select",
                        "label": "Replace Strategy",
                        "default": "first_source_to_all_targets",
                        "options": [
                            "first_source_to_all_targets",
                            "source_order_to_target_order",
                        ],
                        "help": "Bestimmt, ob das erste Source-Face auf alle gefundenen Ziele geht oder ob mehrere Source-Faces der Reihenfolge nach auf erkannte Zielgesichter verteilt werden.",
                    },
                ],
            },
        ],
    },
    {
        "id": "output",
        "label": "Output",
        "description": "Ausgabe, Encoding und Browser-Runner fuers LAN-Setup.",
        "sections": [
            {
                "id": "output-main",
                "title": "Output Folder",
                "controls": [
                    {
                        "scope": "control",
                        "key": "OutputMediaFolder",
                        "type": "text",
                        "label": "Output Folder",
                        "default": DEFAULT_OUTPUT_FOLDER,
                        "help": "Ausgabeordner auf dem GPU-Host.",
                    },
                    {
                        "scope": "control",
                        "key": "OpenOutputToggle",
                        "type": "toggle",
                        "label": "Open Output Folder",
                        "default": False,
                        "help": "In der Web-Workbench normalerweise aus, damit Headless-Runs ruhig bleiben.",
                    },
                    {
                        "scope": "control",
                        "key": "AutoSaveWorkspaceToggle",
                        "type": "toggle",
                        "label": "Auto Save Workspace",
                        "default": False,
                        "help": "Optionalen Workspace-Snapshot nach dem Lauf schreiben.",
                    },
                ],
            },
            {
                "id": "output-ffmpeg",
                "title": "Encoding",
                "controls": [
                    {
                        "scope": "control",
                        "key": "FFMpegOptionsToggle",
                        "type": "toggle",
                        "label": "Show FFmpeg Options",
                        "default": False,
                        "help": "Aktiviert die nativen FFmpeg-Optionen fuer Videoausgabe.",
                    },
                    {
                        "scope": "control",
                        "key": "FFPresetsSDRSelection",
                        "type": "select",
                        "label": "Preset SDR",
                        "default": "p5",
                        "options": ["p1", "p2", "p3", "p4", "p5", "p6", "p7"],
                        "parentToggle": "FFMpegOptionsToggle",
                        "requiredToggleValue": True,
                        "help": "NVENC-Preset fuer SDR-Videos.",
                    },
                    {
                        "scope": "control",
                        "key": "FFQualitySlider",
                        "type": "range",
                        "label": "Quality",
                        "default": 18,
                        "min": 0,
                        "max": 51,
                        "step": 1,
                        "parentToggle": "FFMpegOptionsToggle",
                        "requiredToggleValue": True,
                        "help": "Niedriger = bessere Qualitaet, groessere Datei.",
                    },
                    {
                        "scope": "control",
                        "key": "FFSpatialAQToggle",
                        "type": "toggle",
                        "label": "Spatial AQ",
                        "default": False,
                        "parentToggle": "FFMpegOptionsToggle",
                        "requiredToggleValue": True,
                        "help": "Verteilt Bits staerker auf texturreiche Bereiche.",
                    },
                    {
                        "scope": "control",
                        "key": "FFTemporalAQToggle",
                        "type": "toggle",
                        "label": "Temporal AQ",
                        "default": False,
                        "parentToggle": "FFMpegOptionsToggle",
                        "requiredToggleValue": True,
                        "help": "Glaettet Qualitaet ueber mehrere Frames hinweg.",
                    },
                ],
            },
        ],
    },
]


def _default_scope_values(scope: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for tab in WORKBENCH_TABS:
        for section in tab["sections"]:
            for control in section["controls"]:
                if control["scope"] == scope:
                    values[control["key"]] = copy.deepcopy(control["default"])
    return values


DEFAULT_WORKBENCH_STATE: dict[str, Any] = {
    "control": _default_scope_values("control"),
    "parameters": _default_scope_values("parameters"),
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    temp_path.replace(path)


def normalize_state(payload: dict[str, Any] | None) -> dict[str, Any]:
    normalized = copy.deepcopy(DEFAULT_WORKBENCH_STATE)
    if not isinstance(payload, dict):
        return normalized

    for scope in ("control", "parameters"):
        values = payload.get(scope)
        if not isinstance(values, dict):
            continue
        for key, value in values.items():
            if key in normalized[scope]:
                normalized[scope][key] = value

    output_folder = str(normalized["control"].get("OutputMediaFolder", "")).strip()
    normalized["control"]["OutputMediaFolder"] = output_folder or DEFAULT_OUTPUT_FOLDER
    return normalized


def read_state() -> dict[str, Any]:
    return normalize_state(_read_json(WORKBENCH_DRAFT_PATH))


def write_state(payload: dict[str, Any] | None) -> dict[str, Any]:
    normalized = normalize_state(payload)
    _write_json(WORKBENCH_DRAFT_PATH, normalized)
    return normalized


def schema_payload() -> dict[str, Any]:
    return {
        "tabs": copy.deepcopy(WORKBENCH_TABS),
        "defaults": copy.deepcopy(DEFAULT_WORKBENCH_STATE),
        "state": read_state(),
    }
