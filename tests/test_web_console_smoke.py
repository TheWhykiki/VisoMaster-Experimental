from __future__ import annotations

import base64
import contextlib
import json
import re
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock
from urllib.error import HTTPError

from app.services import browser_workflow, web_processing, web_workbench
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
        self.assertIn("window.localStorage.removeItem(LAYOUT_STORAGE_KEY)", source)

    def test_german_translation_uses_window_title_helper(self) -> None:
        source = (ROOT / "app" / "ui" / "translations" / "de.py").read_text(encoding="utf-8")
        self.assertIn("def _set_window_title(widget, title: str) -> None:", source)
        self.assertIn('(window, _set_window_title, "VisoMaster v0.1.6 - Fusion")', source)
        self.assertNotIn("(window, window.setWindowTitle,", source)
        self.assertIn('if hasattr(widget, "setTitle"):', source)
        self.assertIn("widget.setWindowTitle(title)", source)


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
