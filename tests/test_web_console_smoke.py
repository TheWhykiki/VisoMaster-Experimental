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

from app.services import browser_workflow, web_workbench
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
            "Target Videos and Input Faces",
            "Control Options",
            "Swap Faces",
            "Utilities",
        ):
            self.assertIn(label, html)


class TestWorkbenchAndWorkflowState(WebConsoleSandboxTestCase):
    def test_workbench_defaults_are_stable(self) -> None:
        schema = web_workbench.schema_payload()
        self.assertEqual(["swap", "restoration", "detect", "output"], [tab["id"] for tab in schema["tabs"]])
        self.assertIn("OutputMediaFolder", schema["defaults"]["control"])
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

        request_payload = browser_workflow.build_run_request(detection_frame=12)
        self.assertEqual(12, request_payload["detectionFrame"])
        self.assertEqual(2, len(request_payload["inputFacePaths"]))
        self.assertEqual(state["outputFolder"], request_payload["outputFolder"])

    def test_frame_preview_is_generated_for_uploaded_image(self) -> None:
        browser_workflow.save_target_upload("target.png", PNG_BYTES)

        preview = browser_workflow.generate_target_preview(0)
        self.assertEqual(0, preview["frameIndex"])
        self.assertTrue(Path(preview["path"]).is_file())

        state = browser_workflow.current_state()
        self.assertEqual(0, state["previewFrame"]["frameIndex"])
        self.assertIn("/api/browser-workflow/preview/frame", state["previewFrame"]["url"])


class TestWebConsoleHttpSmoke(WebConsoleSandboxTestCase):
    def test_http_smoke_for_root_and_workbench_roundtrip(self) -> None:
        with self.start_server() as server:
            root_url = f"http://127.0.0.1:{server.server_address[1]}/"
            with urllib.request.urlopen(root_url, timeout=5) as response:
                html = response.read().decode("utf-8")
            self.assertIn("VisoMaster Web Console", html)
            self.assertIn("Control Options", html)
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
