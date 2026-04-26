from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Any

import numpy
from PIL import Image

if (
    platform.system() != "Windows"
    and not os.environ.get("DISPLAY")
    and not os.environ.get("QT_QPA_PLATFORM")
):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"


from PySide6 import QtCore, QtWidgets

import qdarktheme

import app.helpers.miscellaneous as misc_helpers
from app.helpers.paths import resolve_project_path, project_path
from app.ui.core.proxy_style import ProxyStyle
from app.ui import main_ui
from app.ui.widgets import widget_components
from app.ui.widgets import ui_workers
from app.ui.widgets.actions import common_actions
from app.ui.widgets.actions import card_actions
from app.ui.widgets.actions import job_manager_actions
from app.ui.widgets.actions import list_view_actions
from app.ui.widgets.actions import video_control_actions


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_status_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    temp_path.replace(path)


class SilentJobLoadingDialog:
    def __init__(self, total_steps: int, parent=None):
        self.total_steps = total_steps
        self.parent = parent

    def show(self) -> None:
        return None

    def update_progress(self, current: int, total: int, label: str) -> None:
        return None

    def close(self) -> None:
        return None


class HeadlessMainWindow(main_ui.MainWindow):
    def load_last_workspace(self):
        return None


class Runner:
    def __init__(
        self,
        status_file: Path,
        job_name: str | None = None,
        request_payload: dict[str, Any] | None = None,
    ):
        self.request_payload = request_payload or {}
        self.mode = self.request_payload.get("mode", "job")
        self.job_name = job_name or self.request_payload.get("jobName") or self.request_payload.get("label", "Browser-Lauf")
        self.status_file = status_file
        self.status: dict[str, Any] = {
            "jobName": self.job_name,
            "status": "starting",
            "message": "Headless-Runner wird vorbereitet.",
            "startedAt": _iso_now(),
            "pid": os.getpid(),
            "mode": self.mode,
            "runnerBootstrapped": True,
            "runnerStarted": True,
            "runnerStartedAt": _iso_now(),
        }
        self.started_unix = time.time()
        self.processing_started = False
        self.finished = False
        self.last_message = ""
        self.app: QtWidgets.QApplication | None = None
        self.main_window: HeadlessMainWindow | None = None
        self.progress_timer: QtCore.QTimer | None = None
        self.start_watchdog_timer: QtCore.QTimer | None = None
        self._write_status()

    def _workbench_state(self) -> dict[str, Any]:
        payload = self.request_payload.get("workbench")
        return payload if isinstance(payload, dict) else {}

    def _enable_fast_flux_preview(self) -> None:
        if self.mode != "preview":
            return
        workbench = self.request_payload.get("workbench")
        if not isinstance(workbench, dict):
            return
        parameters = workbench.get("parameters")
        if not isinstance(parameters, dict):
            return
        if parameters.get("SwapModelSelection") != "ACE++ (FLUX)":
            return

        current_steps = int(parameters.get("FluxStepsSlider", 20) or 20)
        current_sequence = int(parameters.get("FluxMaxSequenceLengthSlider", 512) or 512)
        parameters["FluxStepsSlider"] = max(4, min(current_steps, 4))
        parameters["FluxMaxSequenceLengthSlider"] = max(64, min(current_sequence, 256))
        self._write_status(
            status="loading",
            message=(
                "Schnelle FLUX-Vorschau aktiv: "
                f"{parameters['FluxStepsSlider']} Schritte, "
                f"max. Sequenz {parameters['FluxMaxSequenceLengthSlider']}."
            ),
        )

    def _apply_workbench_control(self) -> None:
        if not self.main_window:
            raise RuntimeError("MainWindow ist nicht initialisiert.")

        control_values = self._workbench_state().get("control", {})
        if not isinstance(control_values, dict):
            return

        for key, value in control_values.items():
            self.main_window.control[key] = value

    def _apply_workbench_parameters(self) -> None:
        if not self.main_window:
            raise RuntimeError("MainWindow ist nicht initialisiert.")

        parameter_values = self._workbench_state().get("parameters", {})
        if not isinstance(parameter_values, dict):
            return

        self.main_window.current_widget_parameters = misc_helpers.ParametersDict(
            parameter_values.copy(),
            self.main_window.default_parameters,
        )

        for face_id in list(self.main_window.target_faces.keys()):
            self.main_window.parameters[face_id] = misc_helpers.ParametersDict(
                parameter_values.copy(),
                self.main_window.default_parameters,
            )

    def _write_status(self, **updates: Any) -> None:
        self.status.update(updates)
        self.status["pid"] = os.getpid()
        self.status["updatedAt"] = _iso_now()
        _write_status_file(self.status_file, self.status)

    def report_dialog(self, title: str, message: str, level: str = "warning") -> None:
        entry = f"{title}: {message}"
        self.last_message = entry
        print(f"[runner][{level}] {entry}")
        self._write_status(lastMessage=entry)

    def install_dialog_patches(self) -> None:
        common_actions.create_and_show_messagebox = (
            lambda _main_window, window_title, message, _parent_widget: self.report_dialog(
                window_title, message
            )
        )
        widget_components.JobLoadingDialog = SilentJobLoadingDialog

        def _warning(_parent, title, message, *args, **kwargs):
            self.report_dialog(title, message, "warning")
            return QtWidgets.QMessageBox.Ok

        def _critical(_parent, title, message, *args, **kwargs):
            self.report_dialog(title, message, "error")
            return QtWidgets.QMessageBox.Ok

        def _information(_parent, title, message, *args, **kwargs):
            self.report_dialog(title, message, "info")
            return QtWidgets.QMessageBox.Ok

        def _question(_parent, title, message, *args, **kwargs):
            self.report_dialog(title, message, "question")
            return QtWidgets.QMessageBox.Yes

        QtWidgets.QMessageBox.warning = staticmethod(_warning)
        QtWidgets.QMessageBox.critical = staticmethod(_critical)
        QtWidgets.QMessageBox.information = staticmethod(_information)
        QtWidgets.QMessageBox.question = staticmethod(_question)

    def create_application(self) -> QtWidgets.QApplication:
        app = QtWidgets.QApplication(sys.argv)
        app.setStyle(ProxyStyle())
        stylesheet_path = project_path("app", "ui", "styles", "true_dark_styles.qss")
        with stylesheet_path.open("r", encoding="utf-8") as handle:
            stylesheet = (
                qdarktheme.load_stylesheet(
                    theme="dark", custom_colors={"primary": "#4090a3"}
                )
                + "\n"
                + handle.read()
            )
        app.setStyleSheet(stylesheet)
        app.setQuitOnLastWindowClosed(False)
        return app

    def _load_target_media(self, media_path: str) -> None:
        if not self.main_window:
            raise RuntimeError("MainWindow ist nicht initialisiert.")
        self._write_status(
            status="loading",
            message=f"Zielmedium wird geladen: {Path(media_path).name}",
        )

        list_view_actions.clear_stop_loading_target_media(self.main_window)
        card_actions.clear_target_faces(self.main_window, refresh_frame=False)
        self.main_window.target_videos = {}

        worker = ui_workers.TargetMediaLoaderWorker(
            main_window=self.main_window,
            folder_name=False,
            files_list=[media_path],
        )
        worker.thumbnail_ready.connect(
            partial(list_view_actions.add_media_thumbnail_to_target_videos_list, self.main_window)
        )
        worker.run()
        QtWidgets.QApplication.processEvents()

        if not self.main_window.target_videos:
            raise RuntimeError("Das Zielmedium konnte nicht geladen werden.")

        list(self.main_window.target_videos.values())[0].click()
        QtWidgets.QApplication.processEvents()

    def _load_input_faces(self, input_paths: list[str]) -> None:
        if not self.main_window:
            raise RuntimeError("MainWindow ist nicht initialisiert.")
        self._write_status(
            status="loading",
            message=f"{len(input_paths)} Quellgesicht(er) werden geladen.",
        )

        list_view_actions.clear_stop_loading_input_media(self.main_window)
        card_actions.clear_input_faces(self.main_window)
        self.main_window.input_faces = {}

        worker = ui_workers.InputFacesLoaderWorker(
            main_window=self.main_window,
            folder_name=False,
            files_list=input_paths,
        )
        worker.thumbnail_ready.connect(
            partial(list_view_actions.add_media_thumbnail_to_source_faces_list, self.main_window)
        )
        worker.unload_models_request.connect(self.main_window.handle_unload_request)
        worker.run()
        QtWidgets.QApplication.processEvents()

        if not self.main_window.input_faces:
            raise RuntimeError("In den hochgeladenen Quellbildern wurde kein verwertbares Gesicht gefunden.")

    def _prepare_direct_upload(self) -> None:
        if not self.main_window:
            raise RuntimeError("MainWindow ist nicht initialisiert.")

        target_media_path = self.request_payload.get("targetMediaPath")
        input_face_paths = self.request_payload.get("inputFacePaths", [])
        detection_frame = max(0, int(self.request_payload.get("detectionFrame", 0)))
        output_folder = str(self.request_payload.get("outputFolder", "")).strip()

        if not target_media_path or not Path(target_media_path).is_file():
            raise RuntimeError("Das hochgeladene Zielmedium wurde nicht gefunden.")
        if not input_face_paths:
            raise RuntimeError("Es wurden keine Quellgesichter uebergeben.")
        if not output_folder:
            raise RuntimeError("Der Ausgabeordner fuer den Browser-Direktlauf fehlt.")
        Path(output_folder).mkdir(parents=True, exist_ok=True)

        self._apply_workbench_control()
        self._load_target_media(target_media_path)
        self._load_input_faces(input_face_paths)

        self.main_window.control["OpenOutputToggle"] = False
        self.main_window.control["OutputMediaFolder"] = output_folder
        self.main_window.outputFolderLineEdit.setText(output_folder)
        self.main_window.job_marker_pairs = []
        self.main_window.current_job_name = None
        self.main_window.use_job_name_for_output = False
        self.main_window.output_file_name = None

        if (
            self.main_window.video_processor.file_type == "video"
            and detection_frame > 0
        ):
            max_frame = max(0, int(self.main_window.video_processor.max_frame_number or 0))
            detection_frame = min(detection_frame, max_frame)
            self.main_window.videoSeekSlider.blockSignals(True)
            self.main_window.videoSeekSlider.setValue(detection_frame)
            self.main_window.videoSeekSlider.blockSignals(False)
            self.main_window.video_processor.current_frame_number = detection_frame
            self.main_window.video_processor.process_current_frame()
            QtWidgets.QApplication.processEvents()

        self._write_status(
            status="loading",
            message="Zielgesichter werden im Headless-Runner erkannt.",
        )
        self._detect_target_faces()
        self._write_status(
            status="loading",
            message="Workbench-Parameter und Source-Zuordnung werden angewendet.",
        )
        self._apply_workbench_parameters()
        input_faces = list(self.main_window.input_faces.values())
        assign_strategy = str(
            self.request_payload.get("assignStrategy", "first_source_to_all_targets")
        ).strip()
        for index, target_face in enumerate(self.main_window.target_faces.values()):
            if assign_strategy == "source_order_to_target_order" and input_faces:
                selected_input_face = input_faces[min(index, len(input_faces) - 1)]
            else:
                selected_input_face = input_faces[0]
            target_face.assigned_input_faces = {
                selected_input_face.face_id: selected_input_face.embedding_store
            }
            target_face.assigned_merged_embeddings = {}
            target_face.calculate_assigned_input_embedding()

        list(self.main_window.target_faces.values())[0].click()
        self.main_window.swapfacesButton.setChecked(True)
        self._write_status(
            status="loading",
            message="Swap wird fuer den aktuellen Frame vorbereitet.",
        )
        video_control_actions.process_swap_faces(self.main_window)
        QtWidgets.QApplication.processEvents()

    def _prepare_target_detection(self) -> int:
        if not self.main_window:
            raise RuntimeError("MainWindow ist nicht initialisiert.")

        target_media_path = self.request_payload.get("targetMediaPath")
        detection_frame = max(0, int(self.request_payload.get("detectionFrame", 0)))
        if not target_media_path or not Path(target_media_path).is_file():
            raise RuntimeError("Das hochgeladene Zielmedium wurde nicht gefunden.")

        self._apply_workbench_control()
        self._load_target_media(target_media_path)
        normalized_frame = self._set_detection_frame(detection_frame)
        self._detect_target_faces(allow_empty=True)
        return normalized_frame

    def _set_detection_frame(self, detection_frame: int) -> int:
        if not self.main_window:
            raise RuntimeError("MainWindow ist nicht initialisiert.")

        if (
            self.main_window.video_processor.file_type == "video"
            and detection_frame > 0
        ):
            max_frame = max(0, int(self.main_window.video_processor.max_frame_number or 0))
            detection_frame = min(detection_frame, max_frame)
            self.main_window.videoSeekSlider.blockSignals(True)
            self.main_window.videoSeekSlider.setValue(detection_frame)
            self.main_window.videoSeekSlider.blockSignals(False)
            self.main_window.video_processor.current_frame_number = detection_frame
            self.main_window.video_processor.process_current_frame()
            QtWidgets.QApplication.processEvents()
            return detection_frame
        return 0

    def _detect_target_faces(self, allow_empty: bool = False) -> int:
        if not self.main_window:
            raise RuntimeError("MainWindow ist nicht initialisiert.")
        card_actions.find_target_faces(self.main_window)
        QtWidgets.QApplication.processEvents()
        if not self.main_window.target_faces:
            if allow_empty:
                return 0
            raise RuntimeError(
                "Im Zielmedium konnte kein Zielgesicht erkannt werden. Bitte pruefe das Medium oder waehle bei Videos spaeter einen gueltigen Erkennungsframe."
            )
        return len(self.main_window.target_faces)

    def _save_found_faces_manifest(self, output_dir: str | Path, frame_index: int) -> str:
        if not self.main_window:
            raise RuntimeError("MainWindow ist nicht initialisiert.")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        for child in output_path.iterdir():
            if child.is_file():
                child.unlink()

        faces_payload: list[dict[str, Any]] = []
        for index, target_face in enumerate(self.main_window.target_faces.values(), start=1):
            cropped_face = getattr(target_face, "cropped_face", None)
            if not isinstance(cropped_face, numpy.ndarray):
                continue
            asset_name = f"target_face_{index:02d}.png"
            asset_path = output_path / asset_name
            Image.fromarray(cropped_face[..., ::-1]).save(asset_path, "PNG")
            faces_payload.append(
                {
                    "assetName": (Path("faces") / asset_name).as_posix(),
                    "label": f"Target Face {index}",
                    "faceId": str(target_face.face_id),
                    "frameIndex": int(frame_index),
                    "targetName": Path(self.request_payload.get("targetMediaPath", "")).name,
                }
            )

        manifest_path_raw = str(
            self.request_payload.get("foundFacesManifestPath", "")
        ).strip()
        if not manifest_path_raw:
            raise RuntimeError("Der Manifest-Pfad fuer Zielgesichter fehlt.")
        manifest_path = Path(manifest_path_raw)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "frameIndex": int(frame_index),
                    "targetName": Path(self.request_payload.get("targetMediaPath", "")).name,
                    "faces": faces_payload,
                },
                handle,
                indent=2,
            )
        return str(manifest_path)

    def _job_output_folder(self) -> Path | None:
        if not self.main_window:
            return None
        raw_output = str(self.main_window.control.get("OutputMediaFolder", "")).strip()
        if not raw_output:
            return None
        return resolve_project_path(raw_output)

    def _discover_output_path(self) -> str | None:
        output_dir = self._job_output_folder()
        if output_dir is None or not output_dir.exists():
            return None

        started_at = self.started_unix - 5
        candidates = [
            path
            for path in output_dir.iterdir()
            if path.is_file()
            and path.suffix.lower() in {".mp4", ".png", ".jpg", ".jpeg", ".webm"}
            and path.stat().st_mtime >= started_at
        ]
        if not candidates:
            return None
        newest = max(candidates, key=lambda path: path.stat().st_mtime)
        return str(newest)

    def _save_preview_frame(self, output_path: str | Path) -> str:
        if not self.main_window:
            raise RuntimeError("MainWindow ist nicht initialisiert.")
        frame = self.main_window.video_processor.current_frame.copy()
        if not isinstance(frame, numpy.ndarray):
            raise RuntimeError("Es steht kein berechneter Vorschau-Frame zur Verfuegung.")

        target_path = Path(output_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        preview_frame = frame[..., ::-1]
        Image.fromarray(preview_frame).save(target_path, "PNG")
        return str(target_path)

    def _progress_payload(self) -> dict[str, Any]:
        if not self.main_window:
            return {}

        video_processor = self.main_window.video_processor
        payload: dict[str, Any] = {
            "processing": bool(video_processor.processing),
            "recording": bool(video_processor.recording),
            "processingSegments": bool(video_processor.is_processing_segments),
            "mediaType": video_processor.file_type,
        }

        max_frame = getattr(video_processor, "max_frame_number", None)
        start_frame = getattr(video_processor, "processing_start_frame", 0) or 0
        current_frame = getattr(video_processor, "next_frame_to_display", 0) or 0
        if isinstance(max_frame, int) and max_frame > 0:
            total_frames = max(1, max_frame - start_frame + 1)
            processed_frames = max(0, current_frame - start_frame)
            payload["frame"] = current_frame
            payload["frameMax"] = max_frame
            payload["percent"] = round(min(100.0, (processed_frames / total_frames) * 100), 1)

        segments = getattr(video_processor, "segments_to_process", []) or []
        if segments:
            payload["segmentIndex"] = max(0, getattr(video_processor, "current_segment_index", 0))
            payload["segmentTotal"] = len(segments)

        return payload

    def _start_watchdog(self) -> None:
        self.start_watchdog_timer = QtCore.QTimer()
        self.start_watchdog_timer.setSingleShot(True)
        self.start_watchdog_timer.timeout.connect(
            lambda: self.fail(
                self.last_message
                or "Die Verarbeitung wurde gestartet, aber es kam kein Startsignal der Pipeline an."
            )
        )
        self.start_watchdog_timer.start(20000)

    def on_processing_started(self) -> None:
        self.processing_started = True
        if self.start_watchdog_timer:
            self.start_watchdog_timer.stop()
        self._write_status(
            status="running",
            message=f'Job "{self.job_name}" wird verarbeitet.',
            processingStarted=True,
        )

    def _validate_launch(self) -> None:
        if self.finished or self.processing_started or not self.main_window:
            return
        video_processor = self.main_window.video_processor
        if video_processor.processing or video_processor.recording:
            return
        self.fail(
            self.last_message
            or "Der Job konnte nicht gestartet werden. Bitte Output-Ordner, FFmpeg und gespeicherten Job-Inhalt pruefen."
        )

    def on_progress_tick(self) -> None:
        if self.finished or not self.main_window:
            return

        payload = self._progress_payload()
        next_status = "running" if self.processing_started else "loading"
        self._write_status(status=next_status, progress=payload)

        video_processor = self.main_window.video_processor
        if self.processing_started and not video_processor.processing and not video_processor.recording and not video_processor.is_processing_segments:
            self.finish_success()

    def start_job(self) -> None:
        if not self.main_window:
            self.fail("Das Headless-Fenster konnte nicht initialisiert werden.")
            return

        if self.mode == "preview":
            self._write_status(
                status="loading",
                message="Geswappte Vorschau wird in der Desktop-Pipeline berechnet.",
            )
            try:
                self._enable_fast_flux_preview()
                self._prepare_direct_upload()
                preview_output_path = str(
                    self.request_payload.get("previewOutputPath", "")
                ).strip()
                if not preview_output_path:
                    raise RuntimeError("Der Preview-Ausgabepfad fehlt.")
                saved_path = self._save_preview_frame(preview_output_path)
            except Exception as exc:
                self.fail(str(exc))
                return
            self.finish_success(
                message="Geswappte Vorschau wurde erfolgreich erzeugt.",
                output_path=saved_path,
            )
            return

        if self.mode == "find_faces":
            self._write_status(
                status="loading",
                message="Zielgesichter werden im aktuellen Detection Frame gesucht.",
            )
            try:
                frame_index = self._prepare_target_detection()
                found_faces_dir = str(self.request_payload.get("foundFacesDir", "")).strip()
                if not found_faces_dir:
                    raise RuntimeError("Der Ausgabeordner fuer gefundene Zielgesichter fehlt.")
                manifest_path = self._save_found_faces_manifest(found_faces_dir, frame_index)
            except Exception as exc:
                self.fail(str(exc))
                return
            self.finish_success(
                message=f"{len(self.main_window.target_faces)} Zielgesicht(er) wurden erkannt.",
                output_path=manifest_path,
            )
            return

        if self.mode == "upload":
            self._write_status(
                status="loading",
                message="Direkt-Upload wird in die Desktop-Pipeline geladen.",
            )
            try:
                self._prepare_direct_upload()
            except Exception as exc:
                self.fail(str(exc))
                return

            media_type = self.main_window.video_processor.file_type
            if media_type == "image":
                try:
                    video_control_actions.save_current_frame_to_file(self.main_window)
                except Exception as exc:
                    self.fail(f"Das Bild konnte nicht gespeichert werden: {exc}")
                    return
                self.finish_success(message="Direkt-Upload-Bild wurde erfolgreich verarbeitet.")
                return

            self._start_watchdog()
            self.main_window.job_manager_initiated_record = False
            self.main_window.buttonMediaRecord.toggle()
            QtCore.QTimer.singleShot(800, self._validate_launch)
            return

        self._write_status(
            status="loading",
            message=f'Job "{self.job_name}" wird in die Desktop-Pipeline geladen.',
        )

        try:
            job_manager_actions.load_job_by_name(self.main_window, self.job_name)
            QtWidgets.QApplication.processEvents()
        except Exception as exc:
            self.fail(f'Job "{self.job_name}" konnte nicht geladen werden: {exc}')
            return

        self.main_window.control["OpenOutputToggle"] = False
        self.main_window.control["AutoSaveWorkspaceToggle"] = False
        self.main_window.liveSoundButton.setChecked(False)

        output_folder = str(self.main_window.control.get("OutputMediaFolder", "")).strip()
        if not output_folder:
            self.fail(
                'Im Job ist kein "OutputMediaFolder" gesetzt. Bitte den Job in der Desktop-GUI oder im JSON-Editor ergaenzen.'
            )
            return

        if not self.main_window.selected_video_button:
            self.fail("Der Job enthaelt kein geladenes Zielmedium.")
            return

        media_type = self.main_window.video_processor.file_type
        if media_type == "image":
            try:
                video_control_actions.process_swap_faces(self.main_window)
                video_control_actions.save_current_frame_to_file(self.main_window)
            except Exception as exc:
                self.fail(f"Das Bild konnte nicht verarbeitet werden: {exc}")
                return
            self.finish_success(message=f'Bild-Job "{self.job_name}" wurde gespeichert.')
            return

        self._start_watchdog()
        self.main_window.job_manager_initiated_record = True
        self.main_window.buttonMediaRecord.toggle()
        QtCore.QTimer.singleShot(800, self._validate_launch)

    def finish_success(
        self,
        message: str | None = None,
        output_path: str | None = None,
    ) -> None:
        if self.finished:
            return
        self.finished = True
        resolved_output_path = output_path or self._discover_output_path()
        self._write_status(
            status="succeeded",
            message=message or f'Job "{self.job_name}" wurde erfolgreich verarbeitet.',
            progress=self._progress_payload(),
            outputPath=resolved_output_path,
            finishedAt=_iso_now(),
        )
        print(f"[runner] Job {self.job_name} finished successfully.")
        QtCore.QTimer.singleShot(150, self.app.quit)

    def fail(self, message: str) -> None:
        if self.finished:
            return
        self.finished = True
        if self.main_window:
            try:
                self.main_window.video_processor.stop_processing()
            except Exception:
                pass
        self._write_status(
            status="failed",
            message=message,
            progress=self._progress_payload(),
            finishedAt=_iso_now(),
        )
        print(f"[runner][failed] {message}")
        QtCore.QTimer.singleShot(150, self.app.quit)

    def run(self) -> int:
        self.install_dialog_patches()
        self._write_status(
            status="loading",
            message="QApplication wird fuer den Headless-Runner erstellt.",
        )
        self.app = self.create_application()
        self._write_status(
            status="loading",
            message="Headless-MainWindow wird initialisiert.",
        )
        self.main_window = HeadlessMainWindow()
        self.main_window.hide()
        self.main_window.video_processor.processing_started_signal.connect(
            self.on_processing_started
        )

        self.progress_timer = QtCore.QTimer()
        self.progress_timer.timeout.connect(self.on_progress_tick)
        self.progress_timer.start(500)

        QtCore.QTimer.singleShot(0, self.start_job)
        return self.app.exec()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a saved VisoMaster job in a hidden desktop pipeline for the web console."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--job", help="Name des gespeicherten Jobs.")
    group.add_argument(
        "--request-file",
        help="JSON-Datei mit einem direkten Browser-Workflow oder einem erweiterten Startauftrag.",
    )
    parser.add_argument(
        "--status-file",
        required=True,
        help="JSON-Datei fuer Status-Updates der Web-Verarbeitung.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request_payload = None
    if args.request_file:
        with Path(args.request_file).open("r", encoding="utf-8") as handle:
            request_payload = json.load(handle)
    runner = Runner(
        status_file=Path(args.status_file),
        job_name=args.job,
        request_payload=request_payload,
    )
    return runner.run()


if __name__ == "__main__":
    raise SystemExit(main())
