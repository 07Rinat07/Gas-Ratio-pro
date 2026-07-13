"""Run large-LAS visualization performance acceptance checks."""

from __future__ import annotations

import argparse
import json
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--points", type=int, nargs="+", default=[25_000, 100_000])
    parser.add_argument("--curves", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cases = tuple(
        VisualizationBenchmarkCase(f"las-{point_count}", point_count=point_count, curve_count=args.curves)
        for point_count in args.points
    )
    report = run_visualization_benchmark_suite(cases, VisualizationPerformanceGate())
    payload = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
    print(payload)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
