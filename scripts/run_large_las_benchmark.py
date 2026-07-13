"""Run large-LAS visualization performance acceptance checks."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.visualization_performance_acceptance import (
    VisualizationBenchmarkCase,
    VisualizationPerformanceGate,
    run_visualization_benchmark_suite,
)


def _append_github_summary(markdown: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
    if not summary_path:
        return
    with Path(summary_path).open("a", encoding="utf-8") as stream:
        stream.write(markdown)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--points", type=int, nargs="+", default=[25_000, 100_000])
    parser.add_argument("--curves", type=int, default=4)
    parser.add_argument("--output", type=Path, help="Write machine-readable JSON report")
    parser.add_argument("--summary-output", type=Path, help="Write Markdown release summary")
    parser.add_argument(
        "--github-summary",
        action="store_true",
        help="Append Markdown summary to GITHUB_STEP_SUMMARY when available",
    )
    args = parser.parse_args(argv)

    cases = tuple(
        VisualizationBenchmarkCase(f"las-{point_count}", point_count=point_count, curve_count=args.curves)
        for point_count in args.points
    )
    report = run_visualization_benchmark_suite(cases, VisualizationPerformanceGate())
    json_payload = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
    markdown_payload = report.to_markdown()
    print(json_payload)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json_payload + "\n", encoding="utf-8")
    if args.summary_output:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(markdown_payload, encoding="utf-8")
    if args.github_summary:
        _append_github_summary(markdown_payload)
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
