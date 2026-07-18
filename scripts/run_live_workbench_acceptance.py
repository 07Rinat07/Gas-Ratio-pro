#!/usr/bin/env python3
"""Run the Gas Ratio Pro stable-promotion live acceptance gate."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.workbench_live_acceptance import LiveWorkbenchAcceptanceRunner  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=None, help="Temporary loopback Streamlit port.")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "artifacts" / "acceptance" / "live_workbench_acceptance.json",
        help="JSON report path.",
    )
    parser.add_argument("--startup-timeout", type=float, default=60.0)
    parser.add_argument("--app-timeout", type=float, default=120.0)
    args = parser.parse_args()

    report = LiveWorkbenchAcceptanceRunner(
        PROJECT_ROOT,
        port=args.port,
        startup_timeout_seconds=args.startup_timeout,
        app_timeout_seconds=args.app_timeout,
    ).run()
    output = report.write_json(args.output)
    status = "PASSED" if report.passed else "FAILED"
    print(f"Live Workbench acceptance: {status}")
    print(f"Build: {report.build_version} ({report.build_channel})")
    print(f"Source: {report.project_root}")
    print(f"Checks: {sum(check.passed for check in report.checks)}/{len(report.checks)}")
    print(f"Report: {output}")
    for check in report.checks:
        marker = "PASS" if check.passed else "FAIL"
        print(f"[{marker}] {check.check_id}: {check.summary}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
