from __future__ import annotations

import argparse
import contextlib
import json
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def make_face_fixture(path: Path, *, theme: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    colors = {
        "target": ((42, 56, 75), (230, 184, 142), (48, 38, 34)),
        "source": ((70, 42, 54), (210, 154, 112), (34, 30, 28)),
        "swap": ((24, 58, 62), (228, 166, 132), (34, 64, 94)),
    }
    bg, skin, accent = colors[theme]
    image = Image.new("RGB", (256, 256), bg)
    draw = ImageDraw.Draw(image)
    draw.ellipse((66, 36, 190, 176), fill=skin, outline=accent, width=4)
    draw.arc((74, 28, 182, 124), 200, 340, fill=accent, width=12)
    draw.ellipse((96, 92, 112, 108), fill=accent)
    draw.ellipse((144, 92, 160, 108), fill=accent)
    draw.arc((104, 118, 154, 150), 15, 165, fill=accent, width=4)
    draw.rectangle((84, 176, 172, 230), fill=accent)
    draw.text((18, 18), f"Flux {theme}", fill=(245, 245, 235))
    image.save(path, "PNG")


class QuietVisoMasterWebHandler:
    @staticmethod
    def build():
        from app.web.server import VisoMasterWebHandler

        class Handler(VisoMasterWebHandler):
            def log_message(self, format: str, *args) -> None:  # noqa: A003
                return None

        return Handler


@contextlib.contextmanager
def isolated_web_state(tmp_path: Path) -> Iterator[None]:
    from app.services import browser_workflow, web_processing, web_workbench

    originals = {
        "workflow_root": browser_workflow.WORKFLOW_ROOT,
        "target_dir": browser_workflow.TARGET_DIR,
        "source_dir": browser_workflow.SOURCE_DIR,
        "preview_dir": browser_workflow.PREVIEW_DIR,
        "output_dir": browser_workflow.OUTPUT_DIR,
        "target_preview_meta_path": browser_workflow.TARGET_PREVIEW_META_PATH,
        "swap_preview_meta_path": browser_workflow.SWAP_PREVIEW_META_PATH,
        "detected_faces_meta_path": browser_workflow.DETECTED_FACES_META_PATH,
        "workbench_dir": web_workbench.WORKBENCH_DIR,
        "workbench_draft_path": web_workbench.WORKBENCH_DRAFT_PATH,
        "default_output_folder": web_workbench.DEFAULT_OUTPUT_FOLDER,
        "default_workbench_state": json.loads(
            json.dumps(web_workbench.DEFAULT_WORKBENCH_STATE)
        ),
        "processing_dir": web_processing.PROCESSING_DIR,
        "status_file": web_processing.STATUS_FILE,
        "preview_status_file": web_processing.PREVIEW_STATUS_FILE,
        "log_file": web_processing.LOG_FILE,
        "preview_log_file": web_processing.PREVIEW_LOG_FILE,
    }
    original_output_defaults = []
    for tab in web_workbench.WORKBENCH_TABS:
        for section in tab.get("sections", []):
            for control in section.get("controls", []):
                if control.get("key") == "OutputMediaFolder":
                    original_output_defaults.append((control, control.get("default")))

    workflow_root = tmp_path / "workflow"
    preview_dir = workflow_root / "preview"
    output_dir = tmp_path / "outputs"
    processing_dir = tmp_path / "processing"

    browser_workflow.WORKFLOW_ROOT = workflow_root
    browser_workflow.TARGET_DIR = workflow_root / "target"
    browser_workflow.SOURCE_DIR = workflow_root / "sources"
    browser_workflow.PREVIEW_DIR = preview_dir
    browser_workflow.OUTPUT_DIR = output_dir
    browser_workflow.TARGET_PREVIEW_META_PATH = preview_dir / "target_frame.json"
    browser_workflow.SWAP_PREVIEW_META_PATH = preview_dir / "swap_preview.json"
    browser_workflow.DETECTED_FACES_META_PATH = preview_dir / "detected_faces.json"

    web_workbench.WORKBENCH_DIR = workflow_root
    web_workbench.WORKBENCH_DRAFT_PATH = workflow_root / "swap_workbench.json"
    web_workbench.DEFAULT_OUTPUT_FOLDER = str(output_dir)
    web_workbench.DEFAULT_WORKBENCH_STATE["control"]["OutputMediaFolder"] = str(
        output_dir
    )
    for tab in web_workbench.WORKBENCH_TABS:
        for section in tab.get("sections", []):
            for control in section.get("controls", []):
                if control.get("key") == "OutputMediaFolder":
                    control["default"] = str(output_dir)

    web_processing.PROCESSING_DIR = processing_dir
    web_processing.STATUS_FILE = processing_dir / "status.json"
    web_processing.PREVIEW_STATUS_FILE = processing_dir / "preview_status.json"
    web_processing.LOG_FILE = processing_dir / "runner.log"
    web_processing.PREVIEW_LOG_FILE = processing_dir / "preview_runner.log"

    for path in (
        browser_workflow.TARGET_DIR,
        browser_workflow.SOURCE_DIR,
        browser_workflow.PREVIEW_DIR,
        browser_workflow.OUTPUT_DIR,
        web_processing.PROCESSING_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)

    web_workbench.write_state(None)
    try:
        yield
    finally:
        for key, value in originals.items():
            setattr(
                browser_workflow
                if key
                in {
                    "workflow_root",
                    "target_dir",
                    "source_dir",
                    "preview_dir",
                    "output_dir",
                    "target_preview_meta_path",
                    "swap_preview_meta_path",
                    "detected_faces_meta_path",
                }
                else web_workbench
                if key
                in {
                    "workbench_dir",
                    "workbench_draft_path",
                    "default_output_folder",
                    "default_workbench_state",
                }
                else web_processing,
                {
                    "workflow_root": "WORKFLOW_ROOT",
                    "target_dir": "TARGET_DIR",
                    "source_dir": "SOURCE_DIR",
                    "preview_dir": "PREVIEW_DIR",
                    "output_dir": "OUTPUT_DIR",
                    "target_preview_meta_path": "TARGET_PREVIEW_META_PATH",
                    "swap_preview_meta_path": "SWAP_PREVIEW_META_PATH",
                    "detected_faces_meta_path": "DETECTED_FACES_META_PATH",
                    "workbench_dir": "WORKBENCH_DIR",
                    "workbench_draft_path": "WORKBENCH_DRAFT_PATH",
                    "default_output_folder": "DEFAULT_OUTPUT_FOLDER",
                    "default_workbench_state": "DEFAULT_WORKBENCH_STATE",
                    "processing_dir": "PROCESSING_DIR",
                    "status_file": "STATUS_FILE",
                    "preview_status_file": "PREVIEW_STATUS_FILE",
                    "log_file": "LOG_FILE",
                    "preview_log_file": "PREVIEW_LOG_FILE",
                }[key],
                value,
            )
        for control, default in original_output_defaults:
            control["default"] = default


@contextlib.contextmanager
def stub_flux_backend() -> Iterator[None]:
    from app.services import browser_workflow, web_processing, web_workbench

    originals = {
        "generate_found_faces": web_processing.generate_found_faces,
        "generate_upload_preview": web_processing.generate_upload_preview,
        "start_upload_run": web_processing.start_upload_run,
    }

    def normalized_flux_state(workbench_state: dict[str, Any] | None) -> dict[str, Any]:
        state = web_workbench.normalize_state(
            workbench_state or browser_workflow.current_state().get("workbench")
        )
        params = state["parameters"]
        if params.get("SwapModelSelection") != "ACE++ (FLUX)":
            raise ValueError("Playwright FLUX audit expected SwapModelSelection=ACE++ (FLUX).")
        if params.get("FluxUseSourceReferenceToggle"):
            raise ValueError("Playwright FLUX audit expects Source Reference to stay disabled for FLUX Fill.")
        return state

    def generate_found_faces(
        detection_frame: int = 0,
        workbench_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_flux_state(workbench_state)
        browser_workflow.clear_detected_faces()
        faces_dir = browser_workflow.found_faces_dir()
        asset_path = faces_dir / "target_face_01.png"
        make_face_fixture(asset_path, theme="target")
        manifest = {
            "frameIndex": int(detection_frame),
            "targetName": browser_workflow.target_media_path().name,
            "faces": [
                {
                    "assetName": "faces/target_face_01.png",
                    "label": "Target Face 1",
                    "faceId": "playwright-target-1",
                    "frameIndex": int(detection_frame),
                    "targetName": browser_workflow.target_media_path().name,
                }
            ],
        }
        browser_workflow.register_detected_faces(manifest)
        return {
            "message": "1 Zielgesicht(er) gefunden. (Playwright FLUX Stub)",
            "state": browser_workflow.current_state(),
        }

    def generate_upload_preview(
        detection_frame: int = 0,
        workbench_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_flux_state(workbench_state)
        output_path = browser_workflow.swap_preview_output_path()
        make_face_fixture(output_path, theme="swap")
        source_count = len(browser_workflow.current_state().get("sourceFaces") or [])
        browser_workflow.register_swap_preview(
            output_path,
            int(detection_frame),
            source_count=source_count,
        )
        return {
            "message": "Geswappte Vorschau wurde erzeugt. (Playwright FLUX Stub)",
            "state": browser_workflow.current_state(),
        }

    def start_upload_run(
        detection_frame: int = 0,
        workbench_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_flux_state(workbench_state)
        output_dir = Path(browser_workflow.current_state()["outputFolder"])
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "playwright_flux_swap_output.png"
        make_face_fixture(output_path, theme="swap")
        status = web_processing._persist_status(
            {
                "status": "succeeded",
                "mode": "upload",
                "message": "Playwright FLUX Stub Swap erfolgreich abgeschlossen.",
                "startedAt": iso_now(),
                "finishedAt": iso_now(),
                "outputPath": str(output_path),
                "targetMediaPath": str(browser_workflow.target_media_path()),
                "inputFaceCount": len(browser_workflow.current_state().get("sourceFaces") or []),
                "detectionFrame": int(detection_frame),
            }
        )
        return web_processing._normalize_status(status)

    web_processing.generate_found_faces = generate_found_faces
    web_processing.generate_upload_preview = generate_upload_preview
    web_processing.start_upload_run = start_upload_run
    try:
        yield
    finally:
        web_processing.generate_found_faces = originals["generate_found_faces"]
        web_processing.generate_upload_preview = originals["generate_upload_preview"]
        web_processing.start_upload_run = originals["start_upload_run"]


@contextlib.contextmanager
def local_server(host: str, port: int) -> Iterator[str]:
    handler = QuietVisoMasterWebHandler.build()
    server = ThreadingHTTPServer((host, port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    actual_host, actual_port = server.server_address
    url_host = "127.0.0.1" if actual_host in {"0.0.0.0", ""} else actual_host
    try:
        yield f"http://{url_host}:{actual_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def import_playwright():
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Playwright is not installed. Run:\n"
            "  python -m pip install playwright\n"
            "  python -m playwright install chromium"
        ) from exc
    return sync_playwright, PlaywrightTimeoutError


def set_checkbox(page, selector: str, checked: bool) -> None:
    page.locator(selector).wait_for(state="attached")
    page.evaluate(
        """([selector, checked]) => {
            const input = document.querySelector(selector);
            if (!input) {
                throw new Error(`Checkbox not found: ${selector}`);
            }
            input.checked = checked;
            input.dispatchEvent(new Event("input", { bubbles: true }));
            input.dispatchEvent(new Event("change", { bubbles: true }));
        }""",
        [selector, checked],
    )


def wait_for_json(page, path: str, *, timeout_ms: int) -> dict[str, Any]:
    deadline = time.time() + timeout_ms / 1000
    last_payload: dict[str, Any] = {}
    while time.time() < deadline:
        payload = page.evaluate(
            """async (path) => {
                const response = await fetch(path);
                return await response.json();
            }""",
            path,
        )
        if isinstance(payload, dict):
            last_payload = payload
            if payload.get("status") in {"succeeded", "failed", "stopped"}:
                return payload
        time.sleep(1)
    raise TimeoutError(f"Timed out waiting for {path}. Last payload: {last_payload}")


def run_playwright_flow(
    *,
    url: str,
    target_path: Path,
    source_paths: list[Path],
    headless: bool,
    timeout_ms: int,
) -> dict[str, Any]:
    sync_playwright, PlaywrightTimeoutError = import_playwright()
    console_errors: list[str] = []
    page_errors: list[str] = []

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=headless)
        except Exception as exc:
            raise SystemExit(
                "Chromium could not be launched by Playwright. Run:\n"
                "  python -m playwright install chromium"
            ) from exc

        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_selector("#workbenchSections", timeout=timeout_ms)
            page.wait_for_selector("#targetUploadInput", timeout=timeout_ms)

            page.click("#workflowResetButton")
            page.wait_for_selector("#targetMediaPreview", timeout=timeout_ms)

            page.select_option("#workbench-parameters-SwapModelSelection", "ACE++ (FLUX)")
            page.wait_for_selector("#workbench-parameters-FluxModelSelection", timeout=timeout_ms)
            set_checkbox(page, "#workbench-parameters-FluxSettingsEnableToggle", True)
            page.wait_for_selector(
                "#workbench-parameters-FluxUseSourceReferenceToggle",
                timeout=timeout_ms,
            )
            set_checkbox(page, "#workbench-parameters-FluxUseSourceReferenceToggle", False)
            page.fill(
                "#workbench-parameters-FluxPromptText",
                "simple face swap, preserve expression and lighting",
            )
            page.click("#saveWorkbenchButton")

            page.set_input_files("#targetUploadInput", str(target_path))
            with page.expect_response("**/api/browser-workflow/target", timeout=timeout_ms):
                page.click("#uploadTargetButton")
            page.wait_for_selector("#targetMediaPreview img", timeout=timeout_ms)

            page.set_input_files(
                "#sourceUploadInput",
                [str(source_path) for source_path in source_paths],
            )
            with page.expect_response("**/api/browser-workflow/sources", timeout=timeout_ms):
                page.click("#uploadSourcesButton")
            page.wait_for_selector("#sourceFacePreviewList img", timeout=timeout_ms)

            with page.expect_response("**/api/browser-workflow/preview/frame", timeout=timeout_ms):
                page.click("#transportPreviewButton")
            page.wait_for_selector("#stageTargetPreview img", timeout=timeout_ms)

            with page.expect_response("**/api/browser-workflow/find-faces", timeout=timeout_ms):
                page.click("#findTargetFacesButton")
            page.wait_for_selector("#targetFacesPreviewList img", timeout=timeout_ms)

            with page.expect_response("**/api/browser-workflow/preview/swap", timeout=timeout_ms):
                page.click("#transportSwapPreviewButton")
            page.wait_for_selector(
                '#stageComparePreview img[alt="Swapped preview frame"]',
                timeout=timeout_ms,
            )

            with page.expect_response("**/api/browser-workflow/run", timeout=timeout_ms):
                page.click("#workflowRunButton")
            processing_payload = wait_for_json(
                page,
                "/api/processing/status",
                timeout_ms=timeout_ms,
            )

            workflow_payload = page.evaluate(
                """async () => {
                    const response = await fetch('/api/browser-workflow');
                    return await response.json();
                }"""
            )
            if processing_payload.get("status") != "succeeded":
                raise AssertionError(
                    f"Swap did not succeed: {json.dumps(processing_payload, indent=2)}"
                )
            if not processing_payload.get("outputExists"):
                raise AssertionError(
                    f"Swap succeeded without an existing output file: {processing_payload}"
                )
            if not workflow_payload.get("swapPreview"):
                raise AssertionError("Swap preview was not registered in browser workflow.")
            if page_errors:
                raise AssertionError(f"Page errors were reported: {page_errors}")

            return {
                "url": url,
                "target": str(target_path),
                "sources": [str(path) for path in source_paths],
                "processing": processing_payload,
                "workflow": {
                    "detectedFaces": workflow_payload.get("detectedTargetFaces"),
                    "swapPreview": workflow_payload.get("swapPreview"),
                },
                "consoleErrors": console_errors,
            }
        except PlaywrightTimeoutError as exc:
            raise AssertionError(f"Playwright timed out while testing {url}: {exc}") from exc
        finally:
            browser.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a Playwright audit for the Web GUI ACE++ / FLUX swap flow."
    )
    parser.add_argument("--mode", choices=["stub", "real"], default="stub")
    parser.add_argument("--url", help="Use an already running VisoMaster web URL.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--target", type=Path, help="Target image/video for real mode.")
    parser.add_argument(
        "--source",
        action="append",
        type=Path,
        help="Source face image for real mode. Can be passed multiple times.",
    )
    parser.add_argument("--timeout-ms", type=int, default=120000)
    parser.add_argument("--headful", action="store_true")
    parser.add_argument("--json-output", type=Path)
    return parser


def validate_real_assets(args: argparse.Namespace) -> tuple[Path, list[Path]]:
    if args.mode == "stub":
        fixture_dir = Path(tempfile.mkdtemp(prefix="visomaster-flux-fixtures-"))
        target = fixture_dir / "target_face.png"
        source = fixture_dir / "source_face.png"
        make_face_fixture(target, theme="target")
        make_face_fixture(source, theme="source")
        return target, [source]

    if not args.target or not args.target.is_file():
        raise SystemExit("--target must point to an existing image/video in real mode.")
    sources = args.source or []
    if not sources or any(not path.is_file() for path in sources):
        raise SystemExit("--source must be provided at least once and all files must exist in real mode.")
    return args.target, sources


def main() -> int:
    args = build_parser().parse_args()
    target_path, source_paths = validate_real_assets(args)

    temp_context = tempfile.TemporaryDirectory(prefix="visomaster-flux-web-")
    tmp_path = Path(temp_context.name)

    try:
        state_context = (
            contextlib.nullcontext()
            if args.url
            else isolated_web_state(tmp_path)
        )
        backend_context = stub_flux_backend() if args.mode == "stub" else contextlib.nullcontext()

        with state_context, backend_context:
            if args.url:
                result = run_playwright_flow(
                    url=args.url.rstrip("/"),
                    target_path=target_path,
                    source_paths=source_paths,
                    headless=not args.headful,
                    timeout_ms=args.timeout_ms,
                )
            else:
                with local_server(args.host, args.port) as url:
                    result = run_playwright_flow(
                        url=url,
                        target_path=target_path,
                        source_paths=source_paths,
                        headless=not args.headful,
                        timeout_ms=args.timeout_ms,
                    )

        if args.json_output:
            write_json(args.json_output, result)
        print(json.dumps(result, indent=2))
        return 0
    finally:
        temp_context.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
