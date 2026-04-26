from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_step(name: str, command: list[str]) -> tuple[bool, str]:
    print(f"\n[{name}]")
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    output = (completed.stdout or "") + (completed.stderr or "")
    if output.strip():
        print(output.rstrip())

    if completed.returncode == 0:
        print(f"{name}: OK")
        return True, output

    print(f"{name}: FAILED ({completed.returncode})")
    return False, output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the autonomous GUI quality gate for the VisoMaster web console."
    )
    parser.add_argument(
        "--debug-bundle-on-fail",
        action="store_true",
        help="Collect a debug bundle automatically when any gate fails.",
    )
    parser.add_argument(
        "--with-playwright",
        action="store_true",
        help="Run the browser-level Playwright FLUX swap audit in stub mode.",
    )
    args = parser.parse_args()

    python = sys.executable
    checks: list[tuple[str, list[str]]] = [
        (
            "Python compile",
            [
                python,
                "-m",
                "py_compile",
                "app/services/browser_workflow.py",
                "app/services/storage.py",
                "app/services/system_info.py",
                "app/services/web_processing.py",
                "app/services/web_workbench.py",
                "app/web/server.py",
                "app/web/headless_runner_bootstrap.py",
                "app/web/headless_runner.py",
            ],
        ),
        (
            "FLUX ACE++ wrapper tests",
            [
                python,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                "test_flux_ace_plus.py",
            ],
        ),
        (
            "Web processing lifecycle tests",
            [
                python,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                "test_web_processing_lifecycle.py",
            ],
        ),
        (
            "Web console smoke tests",
            [
                python,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                "test_web_console_smoke.py",
            ],
        ),
    ]

    node = shutil.which("node")
    if node:
        checks.insert(
            1,
            (
                "JavaScript syntax",
                [
                    node,
                    "--check",
                    "app/web/static/app.js",
                    "app/web/static/layout.js",
                ],
            ),
        )
    else:
        print("[JavaScript syntax]\nnode not found, skipping syntax check.")

    if args.with_playwright:
        checks.append(
            (
                "Playwright FLUX GUI swap audit",
                [
                    python,
                    "scripts/playwright_flux_swap_audit.py",
                    "--mode",
                    "stub",
                ],
            )
        )

    failures = 0
    for name, command in checks:
        ok, _ = run_step(name, command)
        if not ok:
            failures += 1

    if failures and args.debug_bundle_on_fail:
        bundle_script = ROOT / "scripts" / "collect_web_debug_bundle.py"
        run_step("Debug bundle", [python, str(bundle_script)])

    if failures:
        print(f"\nGUI quality gate failed with {failures} failing step(s).")
        return 1

    print("\nGUI quality gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
