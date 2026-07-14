"""Compare two GASRATIO Pro diagnostics snapshots and enforce a release gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.performance_regression import (
    PerformanceBaseline,
    RegressionPolicy,
    build_performance_baseline,
    compare_performance_baselines,
)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _as_baseline(value: dict) -> PerformanceBaseline:
    if str(value.get("schema") or "").startswith("gasratio.performance-baseline"):
        return PerformanceBaseline.from_dict(value)
    return build_performance_baseline(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--current", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--max-duration-growth-pct", type=float, default=25.0)
    parser.add_argument("--max-duration-growth-ms", type=float, default=250.0)
    parser.add_argument("--max-cache-hit-rate-drop-pct", type=float, default=10.0)
    parser.add_argument("--max-session-key-growth", type=int, default=20)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    policy = RegressionPolicy(
        max_duration_growth_pct=args.max_duration_growth_pct,
        max_duration_growth_ms=args.max_duration_growth_ms,
        max_cache_hit_rate_drop_pct=args.max_cache_hit_rate_drop_pct,
        max_session_key_growth=args.max_session_key_growth,
    )
    report = compare_performance_baselines(
        _as_baseline(_load(args.baseline)),
        _as_baseline(_load(args.current)),
        policy=policy,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    if args.summary_output:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(report.to_markdown(), encoding="utf-8")
    print(report.to_markdown(), end="")
    return 0 if report.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
