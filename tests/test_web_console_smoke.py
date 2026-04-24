from __future__ import annotations

import base64
import contextlib
import json
import os
import re
import shutil
import subprocess
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock
from urllib.error import HTTPError

from PIL import Image

from app.services import browser_workflow, storage, web_processing, web_workbench
from app.web.server import VisoMasterWebHandler


ROOT = Path(__file__).resolve().parents[1]
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
)


class QuietVisoMasterWebHandler(VisoMasterWebHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return None


class WebConsoleSandboxTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        self.originals = {
            "workbench_dir": web_workbench.WORKBENCH_DIR,
            "workbench_draft_path": web_workbench.WORKBENCH_DRAFT_PATH,
            "default_output_folder": web_workbench.DEFAULT_OUTPUT_FOLDER,
            "workflow_root": browser_workflow.WORKFLOW_ROOT,
            "target_dir": browser_workflow.TARGET_DIR,
            "source_dir": browser_workflow.SOURCE_DIR,
            "output_dir": browser_workflow.OUTPUT_DIR,
        }

        workbench_dir = self.temp_path / "workflow"
        target_dir = workbench_dir / "target"
        source_dir = workbench_dir / "sources"
        output_dir = self.temp_path / "outputs"
        for path in (workbench_dir, target_dir, source_dir, output_dir):
            path.mkdir(parents=True, exist_ok=True)

        web_workbench.WORKBENCH_DIR = workbench_dir
        web_workbench.WORKBENCH_DRAFT_PATH = workbench_dir / "swap_workbench.json"
        web_workbench.DEFAULT_OUTPUT_FOLDER = str(output_dir)

        browser_workflow.WORKFLOW_ROOT = workbench_dir
        browser_workflow.TARGET_DIR = target_dir
        browser_workflow.SOURCE_DIR = source_dir
        browser_workflow.OUTPUT_DIR = output_dir

        web_workbench.write_state(None)

    def tearDown(self) -> None:
        web_workbench.WORKBENCH_DIR = self.originals["workbench_dir"]
        web_workbench.WORKBENCH_DRAFT_PATH = self.originals["workbench_draft_path"]
        web_workbench.DEFAULT_OUTPUT_FOLDER = self.originals["default_output_folder"]

        browser_workflow.WORKFLOW_ROOT = self.originals["workflow_root"]
        browser_workflow.TARGET_DIR = self.originals["target_dir"]
        browser_workflow.SOURCE_DIR = self.originals["source_dir"]
        browser_workflow.OUTPUT_DIR = self.originals["output_dir"]

        self.temp_dir.cleanup()

    @contextlib.contextmanager
    def start_server(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), QuietVisoMasterWebHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def request_json(
        self, server: ThreadingHTTPServer, path: str, method: str = "GET", payload: dict | None = None
    ) -> dict:
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        url = f"http://127.0.0.1:{server.server_address[1]}{path}"
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))


class TestWebConsoleStaticContract(unittest.TestCase):
    def test_html_and_js_id_contract_is_consistent(self) -> None:
        html = (ROOT / "app" / "web" / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "app" / "web" / "static" / "app.js").read_text(encoding="utf-8")

        html_ids = set(re.findall(r'id="([^"]+)"', html))
        js_ids = set(re.findall(r'getElementById\("([^"]+)"\)', js))

        self.assertFalse(js_ids - html_ids, f"Missing HTML ids: {sorted(js_ids - html_ids)}")

    def test_html_contains_primary_swap_regions(self) -> None:
        html = (ROOT / "app" / "web" / "static" / "index.html").read_text(encoding="utf-8")
        for label in (
            "Swap Session",
            "Project Library",
            "Swap Parameters",
            "Swap Faces",
            "Preview Frame",
            "Swap Preview",
            "Find Faces",
            "Guided Flow",
        ):
            self.assertIn(label, html)

    def test_stage_target_video_uses_native_controls(self) -> None:
        js = (ROOT / "app" / "web" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="stageTargetVideo"', js)
        self.assertRegex(js, r'id="stageTargetVideo"[\s\S]*?controls')

    def test_html_wires_golden_layout_assets(self) -> None:
        html = (ROOT / "app" / "web" / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="layoutRoot"', html)
        self.assertIn('/static/layout.js', html)
        self.assertIn('/static/vendor/golden-layout/css/goldenlayout-base.css', html)
        self.assertIn('id="panelTemplates"', html)
        self.assertNotIn('id="panelTemplates" hidden', html)
        self.assertTrue((ROOT / "app" / "web" / "static" / "layout.js").is_file())
        self.assertTrue(
            (ROOT / "app" / "web" / "static" / "vendor" / "golden-layout" / "esm" / "index.js").is_file()
        )

    def test_golden_layout_vendor_uses_browser_resolvable_relative_imports(self) -> None:
        vendor_root = ROOT / "app" / "web" / "static" / "vendor" / "golden-layout" / "esm"
        pattern = re.compile(r"(?:from\s+|import\s+)(['\"])(\.[^'\"]+)\1")
        offenders: list[str] = []

        for path in vendor_root.rglob("*.js"):
            text = path.read_text(encoding="utf-8")
            for match in pattern.finditer(text):
                target = match.group(2)
                if target.endswith((".js", ".json", ".css")):
                    continue
                offenders.append(f"{path}: {target}")

        self.assertFalse(offenders, f"Extensionless vendor imports found: {offenders[:10]}")

    def test_layout_script_supports_visible_fallback(self) -> None:
        source = (ROOT / "app" / "web" / "static" / "layout.js").read_text(encoding="utf-8")
        self.assertIn("function setLayoutReady(isReady)", source)
        self.assertIn("reportLayoutFailure", source)
        self.assertIn('const LAYOUT_STORAGE_KEY = "visomaster:web-layout:v6"', source)
        self.assertIn("function clearSavedLayouts()", source)
        self.assertIn("window.localStorage.removeItem(key)", source)
        self.assertIn('"visomaster:web-layout:v2"', source)
        self.assertIn('"visomaster:web-layout:v4"', source)
        self.assertIn('size: "27%"', source)
        self.assertIn('size: "50%"', source)

    def test_german_translation_uses_window_title_helper(self) -> None:
        source = (ROOT / "app" / "ui" / "translations" / "de.py").read_text(encoding="utf-8")
        self.assertIn("def _set_window_title(widget, title: str) -> None:", source)
        self.assertIn('(window, _set_window_title, "VisoMaster v0.1.6 - Fusion")', source)
        self.assertNotIn("(window, window.setWindowTitle,", source)
        self.assertIn('if hasattr(widget, "setTitle"):', source)
        self.assertIn("widget.setWindowTitle(title)", source)

    def test_models_processor_auto_downloads_missing_onnx_models(self) -> None:
        source = (ROOT / "app" / "processors" / "models_processor.py").read_text(encoding="utf-8")
        self.assertIn("def ensure_model_file(self, model_name: str) -> str:", source)
        self.assertIn("model_path = self.ensure_model_file(model_name)", source)
        self.assertIn("download_file(model_name, model_path, model_hash, model_url)", source)
        self.assertIn("could not be downloaded automatically", source)
        self.assertIn("self.ensure_model_file(model_name)", source)

    def test_app_js_contains_guided_workflow_state_machine(self) -> None:
        source = (ROOT / "app" / "web" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function workflowState(payload = state.browserWorkflow)", source)
        self.assertIn("function renderWorkflowGuide(payload)", source)
        self.assertIn('setUiBusy("Swap Preview wird berechnet...")', source)
        self.assertIn('showFlash(workflow.nextAction, true);', source)
        self.assertIn("Outdated Detection", source)

    def test_web_processing_keeps_async_log_handle_open(self) -> None:
        source = (ROOT / "app" / "services" / "web_processing.py").read_text(encoding="utf-8")
        self.assertIn("_PROCESS_LOG_HANDLE = None", source)
        self.assertIn("def _close_process_log_handle() -> None:", source)
        self.assertIn("_PROCESS_LOG_HANDLE = log_handle", source)
        self.assertIn("_close_process_log_handle()", source)


class TestWorkbenchAndWorkflowState(WebConsoleSandboxTestCase):
    def test_workbench_defaults_are_stable(self) -> None:
        schema = web_workbench.schema_payload()
        self.assertEqual(["swap", "restoration", "detect", "output"], [tab["id"] for tab in schema["tabs"]])
        self.assertIn("OutputMediaFolder", schema["defaults"]["control"])
        self.assertIn("BrowserAssignStrategySelection", schema["defaults"]["control"])
        self.assertIn("SwapModelSelection", schema["defaults"]["parameters"])

    def test_browser_workflow_upload_roundtrip_uses_isolated_state(self) -> None:
        browser_workflow.save_target_upload("target.png", PNG_BYTES)
        browser_workflow.save_source_uploads(
            [("source-a.jpg", PNG_BYTES), ("source-b.jpg", PNG_BYTES)]
        )

        state = browser_workflow.current_state()
        self.assertTrue(state["canRun"])
        self.assertEqual("target.png", state["targetMedia"]["name"])
        self.assertEqual(2, len(state["sourceFaces"]))
        self.assertIn("/api/browser-workflow/media/target", state["targetMedia"]["mediaUrl"])
        self.assertIn("mediaUrl", state["sourceFaces"][0])

        request_payload = browser_workflow.build_run_request(
            detection_frame=12,
            workbench_state={
                "control": {"BrowserAssignStrategySelection": "source_order_to_target_order"}
            },
        )
        self.assertEqual(12, request_payload["detectionFrame"])
        self.assertEqual(2, len(request_payload["inputFacePaths"]))
        self.assertEqual(state["outputFolder"], request_payload["outputFolder"])
        self.assertEqual("source_order_to_target_order", request_payload["assignStrategy"])

    def test_frame_preview_is_generated_for_uploaded_image(self) -> None:
        browser_workflow.save_target_upload("target.png", PNG_BYTES)

        preview = browser_workflow.generate_target_preview(0)
        self.assertEqual(0, preview["frameIndex"])
        self.assertTrue(Path(preview["path"]).is_file())

        state = browser_workflow.current_state()
        self.assertEqual(0, state["previewFrame"]["frameIndex"])
        self.assertIn("/api/browser-workflow/preview/frame", state["previewFrame"]["url"])
        self.assertTrue(state["workflow"]["steps"][2]["ready"])

    def test_preview_refresh_clears_stale_detected_faces_and_swap_preview(self) -> None:
        browser_workflow.save_target_upload("target.png", PNG_BYTES)
        browser_workflow.save_source_uploads([("source-a.jpg", PNG_BYTES)])

        preview_path = browser_workflow.swap_preview_output_path()
        preview_path.write_bytes(PNG_BYTES)
        browser_workflow.register_swap_preview(preview_path, frame_index=4, source_count=1)

        faces_dir = browser_workflow.found_faces_dir()
        face_path = faces_dir / "target_face_01.png"
        face_path.write_bytes(PNG_BYTES)
        browser_workflow.register_detected_faces(
            {
                "frameIndex": 4,
                "targetName": "target.png",
                "faces": [
                    {
                        "assetName": "faces/target_face_01.png",
                        "label": "Target Face 1",
                        "faceId": "101",
                        "frameIndex": 4,
                    }
                ],
            }
        )

        browser_workflow.generate_target_preview(0)
        state = browser_workflow.current_state()
        self.assertIsNone(state["swapPreview"])
        self.assertIsNone(state["detectedTargetFaces"])
        self.assertFalse(state["workflow"]["steps"][3]["ready"])
        self.assertFalse(state["workflow"]["steps"][4]["ready"])

    def test_swap_preview_can_be_registered_in_isolated_state(self) -> None:
        browser_workflow.save_target_upload("target.png", PNG_BYTES)
        browser_workflow.save_source_uploads([("source-a.jpg", PNG_BYTES)])
        preview_path = browser_workflow.swap_preview_output_path()
        preview_path.write_bytes(PNG_BYTES)

        preview = browser_workflow.register_swap_preview(
            preview_path,
            frame_index=4,
            source_count=1,
        )
        self.assertEqual(4, preview["frameIndex"])
        self.assertEqual(1, preview["sourceCount"])
        self.assertIn("/api/browser-workflow/preview/swap", preview["url"])

        state = browser_workflow.current_state()
        self.assertEqual(4, state["swapPreview"]["frameIndex"])

    def test_detected_target_faces_can_be_registered_in_isolated_state(self) -> None:
        browser_workflow.save_target_upload("target.png", PNG_BYTES)
        faces_dir = browser_workflow.found_faces_dir()
        face_path = faces_dir / "target_face_01.png"
        face_path.write_bytes(PNG_BYTES)

        detected = browser_workflow.register_detected_faces(
            {
                "frameIndex": 7,
                "targetName": "target.png",
                "faces": [
                    {
                        "assetName": "faces/target_face_01.png",
                        "label": "Target Face 1",
                        "faceId": "101",
                        "frameIndex": 7,
                    }
                ],
            }
        )
        self.assertEqual(1, detected["count"])
        self.assertIn(
            "/api/browser-workflow/faces/faces/target_face_01.png",
            detected["faces"][0]["mediaUrl"],
        )

    def test_detailed_failure_message_ignores_runner_placeholder(self) -> None:
        status_path = self.temp_path / "preview_status.json"
        log_path = self.temp_path / "preview_runner.log"
        status_path.write_text(
            json.dumps({"message": "Headless-Runner wird vorbereitet."}),
            encoding="utf-8",
        )
        log_path.write_text(
            "Traceback...\nRuntimeError: Real runner cause\n",
            encoding="utf-8",
        )

        message = web_processing._detailed_failure_message(  # noqa: SLF001
            status_path,
            log_path,
            "fallback",
        )
        self.assertEqual("RuntimeError: Real runner cause", message)


class TestWebConsoleHttpSmoke(WebConsoleSandboxTestCase):
    def test_http_smoke_for_root_and_workbench_roundtrip(self) -> None:
        with self.start_server() as server:
            root_url = f"http://127.0.0.1:{server.server_address[1]}/"
            with urllib.request.urlopen(root_url, timeout=5) as response:
                html = response.read().decode("utf-8")
            self.assertIn("VisoMaster Web Console", html)
            self.assertIn("Swap Parameters", html)
            self.assertIn("Preview Frame", html)

            payload = self.request_json(server, "/api/workbench")
            self.assertEqual(["swap", "restoration", "detect", "output"], [tab["id"] for tab in payload["tabs"]])

            updated = self.request_json(
                server,
                "/api/workbench",
                method="POST",
                payload={
                    "control": {"OutputMediaFolder": "/tmp/visomaster-quality-gate"},
                    "parameters": {"SimilarityThresholdSlider": 77},
                },
            )
            self.assertEqual("/tmp/visomaster-quality-gate", updated["state"]["control"]["OutputMediaFolder"])
            self.assertEqual(77, updated["state"]["parameters"]["SimilarityThresholdSlider"])

            workflow_state = self.request_json(server, "/api/browser-workflow")
            self.assertEqual("/tmp/visomaster-quality-gate", workflow_state["outputFolder"])

    def test_http_smoke_for_browser_media_and_preview_routes(self) -> None:
        browser_workflow.save_target_upload("target.png", PNG_BYTES)
        browser_workflow.save_source_uploads([("source-a.jpg", PNG_BYTES)])

        with self.start_server() as server:
            payload = self.request_json(
                server,
                "/api/browser-workflow/preview/frame",
                method="POST",
                payload={"frameIndex": 0},
            )
            self.assertEqual(0, payload["previewFrame"]["frameIndex"])

            target_url = f"http://127.0.0.1:{server.server_address[1]}/api/browser-workflow/media/target"
            with urllib.request.urlopen(target_url, timeout=5) as response:
                self.assertGreater(len(response.read()), 0)

            preview_url = f"http://127.0.0.1:{server.server_address[1]}/api/browser-workflow/preview/frame"
            with urllib.request.urlopen(preview_url, timeout=5) as response:
                self.assertGreater(len(response.read()), 0)

    def test_find_faces_returns_runtime_dependency_error_as_json(self) -> None:
        browser_workflow.save_target_upload("target.png", PNG_BYTES)

        with self.start_server() as server, mock.patch.object(
            web_processing,
            "_ensure_runtime_dependencies",
            side_effect=ValueError("Fehlende Python-Pakete: numpy, Pillow"),
        ):
            url = f"http://127.0.0.1:{server.server_address[1]}/api/browser-workflow/find-faces"
            request = urllib.request.Request(
                url,
                data=json.dumps({"frameIndex": 0, "workbench": {}}).encode("utf-8"),
                method="POST",
                headers={"Content-Type": "application/json"},
            )

            with self.assertRaises(HTTPError) as context:
                urllib.request.urlopen(request, timeout=5)

            self.assertEqual(400, context.exception.code)
            payload = json.loads(context.exception.read().decode("utf-8"))
            self.assertEqual("Fehlende Python-Pakete: numpy, Pillow", payload["error"])


class TestWebConsolePlaywrightAudit(WebConsoleSandboxTestCase):
    def test_primary_buttons_and_tabs_are_clickable_in_browser(self) -> None:
        if shutil.which("node") is None:
            self.skipTest("node is required for the Playwright audit")
        if shutil.which("ffmpeg") is None:
            self.skipTest("ffmpeg is required to generate the sample video")

        probe = subprocess.run(
            ["node", "-e", "require('playwright'); console.log('ok')"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if probe.returncode != 0:
            self.skipTest("playwright is not available in node")

        source_image = self.temp_path / "source.png"
        Image.new("RGB", (64, 64), (255, 0, 0)).save(source_image)

        target_video = self.temp_path / "target.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=320x240:d=1",
                "-pix_fmt",
                "yuv420p",
                str(target_video),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )

        sample = {
            "jobs": {"demo-job": {"steps": ["swap"]}},
            "job-exports": {"demo-export": {"steps": ["export"]}},
            "presets": {"demo-preset": {"parameters": {}, "control": {}}},
            "embeddings": {
                "demo-embedding": [
                    {
                        "name": "Demo",
                        "embedding_store": {"Inswapper128ArcFace": [0.1, 0.2]},
                    }
                ]
            },
            "workspace": {"target_faces_data": [1], "input_faces_data": [1], "markers": [1]},
        }
        processing_status = {
            "status": "idle",
            "message": "Noch keine Browser-Verarbeitung gestartet.",
            "updatedAt": "2026-04-19T00:00:00+00:00",
            "logTail": [],
            "active": False,
            "outputExists": False,
        }
        backend_calls: list[dict[str, object]] = []

        def list_items(kind: str) -> list[dict[str, object]]:
            items = []
            for name, payload in sample[kind].items():
                items.append(
                    {
                        "name": name,
                        "modifiedAt": "2026-04-19T00:00:00+00:00",
                        "entryCount": len(payload) if isinstance(payload, dict) else 1,
                        "modelCount": 1,
                        "dimensions": [2],
                    }
                )
            return items

        def current_status() -> dict[str, object]:
            return dict(processing_status)

        def start_job(job_name: str) -> dict[str, object]:
            backend_calls.append({"name": "start_saved_job", "jobName": job_name})
            processing_status.update(
                {
                    "status": "running",
                    "message": f"Job {job_name} started",
                    "jobName": job_name,
                    "active": True,
                    "logTail": ["job start"],
                }
            )
            return dict(processing_status)

        def stop_job() -> dict[str, object]:
            backend_calls.append({"name": "stop_processing"})
            processing_status.update(
                {
                    "status": "stopped",
                    "message": "stopped",
                    "active": False,
                    "logTail": ["job stop"],
                }
            )
            return dict(processing_status)

        def start_upload_run(
            detection_frame: int = 0,
            workbench_state: dict[str, object] | None = None,
        ) -> dict[str, object]:
            backend_calls.append(
                {
                    "name": "run_upload_swap",
                    "detectionFrame": detection_frame,
                    "hasWorkbench": isinstance(workbench_state, dict),
                }
            )
            output = self.temp_path / "outputs" / "result.png"
            Image.new("RGB", (64, 64), (0, 180, 120)).save(output)
            processing_status.update(
                {
                    "status": "succeeded",
                    "message": "Browser-Direktlauf erfolgreich.",
                    "active": False,
                    "outputPath": str(output),
                    "outputExists": True,
                    "outputDownloadUrl": "/api/processing/output",
                    "finishedAt": "2026-04-19T00:00:02+00:00",
                    "logTail": ["upload ok"],
                }
            )
            return dict(processing_status)

        def generate_upload_preview(
            detection_frame: int = 0,
            workbench_state: dict[str, object] | None = None,
        ) -> dict[str, object]:
            backend_calls.append(
                {
                    "name": "swap_preview",
                    "detectionFrame": detection_frame,
                    "hasWorkbench": isinstance(workbench_state, dict),
                }
            )
            preview_path = browser_workflow.swap_preview_output_path()
            Image.new("RGB", (64, 64), (220, 100, 120)).save(preview_path)
            browser_workflow.register_swap_preview(
                preview_path,
                frame_index=detection_frame,
                source_count=len(browser_workflow.current_state()["sourceFaces"]),
            )
            return {"message": "preview ok", "state": browser_workflow.current_state()}

        def generate_found_faces(
            detection_frame: int = 0,
            workbench_state: dict[str, object] | None = None,
        ) -> dict[str, object]:
            backend_calls.append(
                {
                    "name": "find_faces",
                    "detectionFrame": detection_frame,
                    "hasWorkbench": isinstance(workbench_state, dict),
                }
            )
            face_path = browser_workflow.found_faces_dir() / "target_face_01.png"
            Image.new("RGB", (64, 64), (100, 140, 240)).save(face_path)
            browser_workflow.register_detected_faces(
                {
                    "frameIndex": detection_frame,
                    "targetName": browser_workflow.current_state()["targetMedia"]["name"],
                    "faces": [
                        {
                            "assetName": "faces/target_face_01.png",
                            "label": "Target Face 1",
                            "faceId": "1",
                            "frameIndex": detection_frame,
                        }
                    ],
                }
            )
            return {
                "message": "1 Zielgesicht(er) gefunden.",
                "state": browser_workflow.current_state(),
            }

        def fake_generate_target_preview(frame_index: int = 0) -> dict[str, object]:
            backend_calls.append({"name": "target_preview", "frameIndex": frame_index})
            target = browser_workflow.target_media_path()
            asset_path = browser_workflow.PREVIEW_DIR / "target_frame.jpg"
            browser_workflow.clear_detected_faces()
            Image.new("RGB", (64, 64), (123, 50, 200)).save(asset_path)
            browser_workflow._write_json(  # noqa: SLF001
                browser_workflow.TARGET_PREVIEW_META_PATH,
                {
                    "assetName": asset_path.name,
                    "frameIndex": int(frame_index),
                    "fileType": "video" if target.suffix.lower() == ".mp4" else "image",
                    "targetName": target.name,
                    "updatedAt": "2026-04-19T00:00:01+00:00",
                },
            )
            return browser_workflow._preview_state()  # noqa: SLF001

        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(storage, "list_jobs", lambda: list_items("jobs")))
            stack.enter_context(
                mock.patch.object(storage, "list_job_exports", lambda: list_items("job-exports"))
            )
            stack.enter_context(mock.patch.object(storage, "list_presets", lambda: list_items("presets")))
            stack.enter_context(
                mock.patch.object(storage, "list_embeddings", lambda: list_items("embeddings"))
            )
            stack.enter_context(
                mock.patch.object(storage, "read_job", lambda name: sample["jobs"][name])
            )
            stack.enter_context(
                mock.patch.object(
                    storage, "read_job_export", lambda name: sample["job-exports"][name]
                )
            )
            stack.enter_context(
                mock.patch.object(storage, "read_preset", lambda name: sample["presets"][name])
            )
            stack.enter_context(
                mock.patch.object(
                    storage, "read_embedding", lambda name: sample["embeddings"][name]
                )
            )
            stack.enter_context(
                mock.patch.object(
                    storage,
                    "write_job",
                    lambda name, payload: sample["jobs"].__setitem__(name, payload)
                    or self.temp_path / f"jobs-{name}.json",
                )
            )
            stack.enter_context(
                mock.patch.object(
                    storage,
                    "write_job_export",
                    lambda name, payload: sample["job-exports"].__setitem__(name, payload)
                    or self.temp_path / f"exports-{name}.json",
                )
            )
            stack.enter_context(
                mock.patch.object(
                    storage,
                    "write_preset",
                    lambda name, parameters, control: sample["presets"].__setitem__(
                        name, {"parameters": parameters, "control": control}
                    )
                    or {
                        "preset": self.temp_path / f"presets-{name}.json",
                        "control": self.temp_path / f"presets-{name}-ctl.json",
                    },
                )
            )
            stack.enter_context(
                mock.patch.object(
                    storage,
                    "write_embedding",
                    lambda name, payload: sample["embeddings"].__setitem__(name, payload)
                    or self.temp_path / f"embeddings-{name}.json",
                )
            )
            stack.enter_context(
                mock.patch.object(
                    storage, "delete_job", lambda name: sample["jobs"].pop(name, None)
                )
            )
            stack.enter_context(
                mock.patch.object(
                    storage,
                    "delete_job_export",
                    lambda name: sample["job-exports"].pop(name, None),
                )
            )
            stack.enter_context(
                mock.patch.object(
                    storage, "delete_preset", lambda name: sample["presets"].pop(name, None)
                )
            )
            stack.enter_context(
                mock.patch.object(
                    storage,
                    "delete_embedding",
                    lambda name: sample["embeddings"].pop(name, None),
                )
            )
            stack.enter_context(
                mock.patch.object(
                    storage,
                    "summarize_workspace",
                    lambda: {
                        "exists": True,
                        "targetFaceCount": 1,
                        "inputFaceCount": 1,
                        "markerCount": 1,
                        "modifiedAt": "2026-04-19T00:00:00+00:00",
                    },
                )
            )
            stack.enter_context(
                mock.patch.object(storage, "read_last_workspace", lambda: sample["workspace"])
            )
            stack.enter_context(
                mock.patch.object(
                    storage,
                    "write_last_workspace",
                    lambda payload: sample.__setitem__("workspace", payload)
                    or self.temp_path / "last_workspace.json",
                )
            )

            stack.enter_context(mock.patch.object(web_processing, "current_status", current_status))
            stack.enter_context(mock.patch.object(web_processing, "start_job", start_job))
            stack.enter_context(mock.patch.object(web_processing, "stop_job", stop_job))
            stack.enter_context(mock.patch.object(web_processing, "start_upload_run", start_upload_run))
            stack.enter_context(
                mock.patch.object(web_processing, "generate_upload_preview", generate_upload_preview)
            )
            stack.enter_context(
                mock.patch.object(web_processing, "generate_found_faces", generate_found_faces)
            )

            stack.enter_context(
                mock.patch.object(
                    browser_workflow,
                    "_media_metadata",
                    lambda path: {
                        "width": 320,
                        "height": 240,
                        "fps": 25.0,
                        "frameCount": 100,
                        "frameMax": 99,
                        "durationSeconds": 4.0,
                    }
                    if path.suffix.lower() == ".mp4"
                    else {"width": 64, "height": 64},
                )
            )
            stack.enter_context(
                mock.patch.object(
                    browser_workflow, "generate_target_preview", fake_generate_target_preview
                )
            )

            with self.start_server() as server:
                audit_screenshot = self.temp_path / "webui-e2e-audit.png"
                script = r"""
const { chromium } = require('playwright');

(async () => {
  const pageErrors = [];
  const actionErrors = [];
  const networkErrors = [];
  const clicked = [];
  const checkpoints = [];
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.setDefaultTimeout(5000);
  await page.addInitScript(() => {
    localStorage.setItem('visomaster:web-layout:v1', '{"stale":true}');
    localStorage.setItem('visomaster:web-layout:v2', '{"stale":true}');
    localStorage.setItem('visomaster:web-layout:v3', '{"stale":true}');
    localStorage.setItem('visomaster:web-layout:v4', '{"stale":true}');
    localStorage.setItem('visomaster:web-layout:v5', '{"stale":true}');
  });
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      pageErrors.push(msg.text());
    }
  });
  page.on('response', async (response) => {
    if (response.ok()) {
      return;
    }
    networkErrors.push(`${response.status()} ${response.request().method()} ${response.url()}`);
  });

  function recordCheckpoint(name) {
    checkpoints.push(name);
  }

  async function click(selector, label) {
    try {
      await page.locator(selector).click({ noWaitAfter: true });
      clicked.push(label);
      await page.waitForTimeout(150);
    } catch (error) {
      actionErrors.push(`${label}: ${error.message}`);
    }
  }

  async function requireVisible(selector, label) {
    try {
      const locator = page.locator(selector);
      await locator.waitFor({ state: 'visible', timeout: 5000 });
      const box = await locator.boundingBox();
      if (!box || box.width < 2 || box.height < 2) {
        actionErrors.push(`${label}: visible element has invalid size ${JSON.stringify(box)}`);
      }
    } catch (error) {
      actionErrors.push(`${label}: ${error.message}`);
    }
  }

  async function requireEnabled(selector, label) {
    const disabled = await page.locator(selector).isDisabled();
    if (disabled) {
      actionErrors.push(`${label}: button is disabled`);
    }
  }

  async function waitEnabled(selector, label) {
    try {
      await page.waitForFunction(
        (sel) => {
          const element = document.querySelector(sel);
          return Boolean(element) && !element.disabled;
        },
        selector,
        { timeout: 5000 }
      );
    } catch (error) {
      actionErrors.push(`${label}: ${error.message}`);
    }
  }

  async function requireHitTarget(selector, label) {
    try {
      const hit = await page.locator(selector).evaluate((element) => {
        const rect = element.getBoundingClientRect();
        const points = [
          [rect.left + rect.width / 2, rect.top + rect.height / 2],
          [rect.left + rect.width / 2, rect.bottom - 8],
        ];
        return points.map(([x, y]) => {
          const node = document.elementFromPoint(x, y);
          return {
            ok: node === element || element.contains(node),
            hitTag: node?.tagName || null,
            hitId: node?.id || null,
            hitClass: node?.className || null,
          };
        });
      });
      const blocked = hit.find((entry) => !entry.ok);
      if (blocked) {
        actionErrors.push(`${label}: pointer target blocked by ${JSON.stringify(blocked)}`);
      }
    } catch (error) {
      actionErrors.push(`${label}: ${error.message}`);
    }
  }

  async function requireText(selector, label, expected) {
    try {
      const text = (await page.locator(selector).textContent()) || '';
      if (!text.includes(expected)) {
        actionErrors.push(`${label}: expected "${expected}" in "${text.trim()}"`);
      }
    } catch (error) {
      actionErrors.push(`${label}: ${error.message}`);
    }
  }

  async function waitText(selector, label, expected) {
    try {
      await page.waitForFunction(
        ({ selector, expected }) => {
          const text = document.querySelector(selector)?.textContent || '';
          return text.includes(expected);
        },
        { selector, expected },
        { timeout: 5000 }
      );
    } catch (error) {
      const text = (await page.locator(selector).textContent().catch(() => '')) || '';
      actionErrors.push(`${label}: expected "${expected}" in "${text.trim()}"`);
    }
  }

  try {
    await page.goto(process.env.TEST_BASE_URL, { waitUntil: 'networkidle' });
    await requireVisible('.layout-root .lm_root', 'golden-layout-root');
    for (const selector of ['#panelWorkflow', '#panelViewer', '#panelOutput', '#panelParameters']) {
      await requireVisible(selector, selector);
    }
    const layoutBootstrap = await page.evaluate(() => ({
      ready: document.documentElement.classList.contains('layout-ready'),
      storageKey: window.VisoMasterLayout?.storageKey || null,
      hasReset: typeof window.VisoMasterLayout?.reset === 'function',
      legacyV2: localStorage.getItem('visomaster:web-layout:v2'),
      current: localStorage.getItem('visomaster:web-layout:v6'),
    }));
    if (!layoutBootstrap.ready || !layoutBootstrap.hasReset || layoutBootstrap.storageKey !== 'visomaster:web-layout:v6') {
      actionErrors.push(`layout bootstrap invalid: ${JSON.stringify(layoutBootstrap)}`);
    }
    const initialFlash = await page.locator('#globalFlash').textContent();
    if (initialFlash && initialFlash.trim()) {
      actionErrors.push(`initial flash: ${initialFlash.trim()}`);
    }
    recordCheckpoint('loaded-layout');

    await click('#refreshAllButton', 'refreshAllButton');
    await click('#resetLayoutButton', 'resetLayoutButton');
    const layoutAfterReset = await page.evaluate(() => ({
      legacyV1: localStorage.getItem('visomaster:web-layout:v1'),
      legacyV2: localStorage.getItem('visomaster:web-layout:v2'),
      legacyV3: localStorage.getItem('visomaster:web-layout:v3'),
      legacyV4: localStorage.getItem('visomaster:web-layout:v4'),
      legacyV5: localStorage.getItem('visomaster:web-layout:v5'),
      current: localStorage.getItem('visomaster:web-layout:v6'),
    }));
    if (layoutAfterReset.legacyV1 || layoutAfterReset.legacyV2 || layoutAfterReset.legacyV3 || layoutAfterReset.legacyV4 || layoutAfterReset.legacyV5 || !layoutAfterReset.current) {
      actionErrors.push(`layout reset did not clean storage: ${JSON.stringify(layoutAfterReset)}`);
    }
    recordCheckpoint('reset-layout');

    await click('[data-left-dock-tab="library"]', 'leftDock-library');
    await click('[data-refresh="jobs"]', 'refresh-jobs');
    await click('[data-refresh="presets"]', 'refresh-presets');
    await click('[data-refresh="embeddings"]', 'refresh-embeddings');
    await click('[data-refresh="job-exports"]', 'refresh-job-exports');
    await click('#loadWorkspaceButton', 'loadWorkspaceButton');

    await click('[data-left-dock-tab="tools"]', 'leftDock-tools');
    await click('[data-utility-tab="status"]', 'utility-status');
    await click('[data-utility-tab="editor"]', 'utility-editor');
    await click('[data-utility-tab="builder"]', 'utility-builder');
    await page.fill('#builderFileName', 'pw-embed');
    await page.fill('#builderEmbeddingName', 'PW Embed');
    await page.fill('#builderModelName', 'Inswapper128ArcFace');
    await page.fill('#builderVectorInput', '0.1, 0.2, 0.3');
    await click('#builderAddModelButton', 'builderAddModelButton');
    await requireText('#builderStats', 'builderStats', '1 Modell');
    await click('#builderSaveButton', 'builderSaveButton');
    await click('#builderResetButton', 'builderResetButton');
    recordCheckpoint('tools-and-builder');

    await click('[data-left-dock-tab="library"]', 'leftDock-library-2');
    await click('#presetsList .item-button', 'select-preset');
    await page.fill('#nameInput', 'demo-preset-2');
    await page.fill('#jsonEditor', '{"parameters":{},"control":{}}');
    await click('#saveButton', 'saveButton');
    await click('[data-left-dock-tab="library"]', 'leftDock-library-export');
    await click('#jobExportsList .item-button', 'select-export');
    await click('#deleteButton', 'deleteButton');
    recordCheckpoint('library-editor');

    await click('[data-left-dock-tab="media"]', 'leftDock-media');
    await page.setInputFiles('#targetUploadInput', process.env.TEST_TARGET_VIDEO);
    await click('#uploadTargetButton', 'uploadTargetButton');
    await page.setInputFiles('#sourceUploadInput', [process.env.TEST_SOURCE_IMAGE]);
    await click('#uploadSourcesButton', 'uploadSourcesButton');
    await requireVisible('#stageTargetVideo', 'stage target video');
    await requireHitTarget('#stageTargetVideo', 'stage target video controls');
    const targetVideoState = await page.locator('#stageTargetVideo').evaluate((video) => ({
      controls: video.controls,
      muted: video.muted,
      src: video.currentSrc || video.src,
    }));
    if (!targetVideoState.controls || !targetVideoState.src) {
      actionErrors.push(`target video invalid: ${JSON.stringify(targetVideoState)}`);
    }
    await requireVisible('#sourceFacePreviewList .browser-item', 'source face preview card');
    recordCheckpoint('media-uploaded');

    await requireEnabled('#transportPreviewButton', 'transportPreviewButton');
    await click('#transportPreviewButton', 'transportPreviewButton');
    await requireVisible('#stageComparePreview img[alt="Selected target frame preview"]', 'target frame preview image');
    await click('#transportPrevFrameButton', 'transportPrevFrameButton');
    await click('#transportNextFrameButton', 'transportNextFrameButton');
    await click('#transportPlayButton', 'transportPlayButton-play');
    await page.waitForTimeout(200);
    await click('#transportPlayButton', 'transportPlayButton-pause');
    await click('#transportPreviewButton', 'transportPreviewButton-refresh');

    await requireEnabled('#quickFindTargetFacesButton', 'quickFindTargetFacesButton');
    await click('#quickFindTargetFacesButton', 'quickFindTargetFacesButton');
    await waitEnabled('#clearTargetFacesButton', 'clearTargetFacesButton-ready');
    await click('#clearTargetFacesButton', 'clearTargetFacesButton');
    await click('#findTargetFacesButton', 'findTargetFacesButton');
    await waitEnabled('#quickSwapPreviewButton', 'quickSwapPreviewButton-ready');
    await requireVisible('#targetFacesPreviewList .browser-item', 'detected target face card');
    recordCheckpoint('faces-detected');

    await requireEnabled('#quickSwapPreviewButton', 'quickSwapPreviewButton');
    await click('#quickSwapPreviewButton', 'quickSwapPreviewButton');
    await requireVisible('#stageComparePreview img[alt="Swapped preview frame"]', 'swapped preview image');
    await waitEnabled('#quickRunWorkflowButton', 'quickRunWorkflowButton-ready');
    await requireEnabled('#quickRunWorkflowButton', 'quickRunWorkflowButton');
    await click('#quickRunWorkflowButton', 'quickRunWorkflowButton');
    await waitEnabled('#workflowRunButton', 'workflowRunButton-ready');
    await click('#workflowRunButton', 'workflowRunButton');
    await requireVisible('#stageComparePreview img[alt="Swap output preview"]', 'processing output image');
    recordCheckpoint('swap-preview-and-run');

    await click('[data-center-pane-tab="log"]', 'centerPane-log');
    await click('[data-center-pane-tab="notes"]', 'centerPane-notes');
    await click('[data-center-pane-tab="output"]', 'centerPane-output');
    await click('#processingRefreshButton', 'processingRefreshButton');

    await click('[data-left-dock-tab="library"]', 'leftDock-library-3');
    await click('#jobsList .item-button', 'select-job');
    await requireEnabled('#processingStartButton', 'processingStartButton');
    await click('#processingStartButton', 'processingStartButton');
    await requireEnabled('#processingStopButton', 'processingStopButton');
    await click('#processingStopButton', 'processingStopButton');
    recordCheckpoint('saved-job-controls');

    await click('[data-left-dock-tab="media"]', 'leftDock-media-2');
    await click('#workflowResetButton', 'workflowResetButton');
    await waitText('#workflowSummary', 'workflow reset summary', 'Lade zuerst das Zielmedium');

    await click('[data-workbench-tab="swap"]', 'workbench-swap');
    await click('[data-workbench-tab="restoration"]', 'workbench-restoration');
    await click('[data-workbench-tab="detect"]', 'workbench-detect');
    await click('[data-workbench-tab="output"]', 'workbench-output');
    await click('#saveWorkbenchButton', 'saveWorkbenchButton');
    await click('#resetWorkbenchButton', 'resetWorkbenchButton');
    recordCheckpoint('workbench-tabs');

    const finalFlash = await page.locator('#globalFlash').textContent();
    if (process.env.TEST_AUDIT_SCREENSHOT) {
      await page.screenshot({ path: process.env.TEST_AUDIT_SCREENSHOT, fullPage: true });
    }
    console.log(JSON.stringify({ clicked, checkpoints, pageErrors, networkErrors, actionErrors, finalFlash }, null, 2));
  } finally {
    await browser.close();
  }
})();
"""

                result = subprocess.run(
                    ["node", "-e", script],
                    cwd=ROOT,
                    env={
                        **os.environ,
                        "TEST_BASE_URL": f"http://127.0.0.1:{server.server_address[1]}/",
                        "TEST_TARGET_VIDEO": str(target_video),
                        "TEST_SOURCE_IMAGE": str(source_image),
                        "TEST_AUDIT_SCREENSHOT": str(audit_screenshot),
                    },
                    capture_output=True,
                    text=True,
                    timeout=90,
                    check=False,
                )

        self.assertEqual(
            0,
            result.returncode,
            msg=f"Playwright audit failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
        )
        payload = json.loads(result.stdout.strip())
        self.assertFalse(payload["pageErrors"], payload)
        self.assertFalse(payload["networkErrors"], payload)
        self.assertFalse(payload["actionErrors"], payload)
        self.assertTrue(audit_screenshot.is_file(), payload)
        self.assertLess(1000, audit_screenshot.stat().st_size, payload)
        expected_checkpoints = {
            "loaded-layout",
            "reset-layout",
            "tools-and-builder",
            "library-editor",
            "media-uploaded",
            "faces-detected",
            "swap-preview-and-run",
            "saved-job-controls",
            "workbench-tabs",
        }
        self.assertTrue(expected_checkpoints.issubset(set(payload["checkpoints"])), payload)
        expected_clicks = {
            "refreshAllButton",
            "resetLayoutButton",
            "uploadTargetButton",
            "uploadSourcesButton",
            "findTargetFacesButton",
            "clearTargetFacesButton",
            "loadWorkspaceButton",
            "saveButton",
            "deleteButton",
            "builderResetButton",
            "builderSaveButton",
            "builderAddModelButton",
            "transportPrevFrameButton",
            "transportPlayButton-play",
            "transportPlayButton-pause",
            "transportNextFrameButton",
            "transportPreviewButton",
            "quickFindTargetFacesButton",
            "quickSwapPreviewButton",
            "quickRunWorkflowButton",
            "workflowRunButton",
            "processingStartButton",
            "processingStopButton",
            "processingRefreshButton",
            "workflowResetButton",
            "resetWorkbenchButton",
            "saveWorkbenchButton",
        }
        self.assertTrue(expected_clicks.issubset(set(payload["clicked"])), payload)
        self.assertTrue(
            {
                "target_preview",
                "find_faces",
                "swap_preview",
                "run_upload_swap",
                "start_saved_job",
                "stop_processing",
            }.issubset({str(call["name"]) for call in backend_calls}),
            backend_calls,
        )
