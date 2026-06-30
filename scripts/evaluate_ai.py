from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.evaluation import AI_EVAL_PROVIDER_MODES, run_ai_evaluation  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate local AI assistant retrieval quality.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--provider-mode",
        choices=tuple(sorted(AI_EVAL_PROVIDER_MODES)),
        default="offline-docs",
        help="Use offline-docs provider or provider from config/ai.json.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    report = run_ai_evaluation(root=PROJECT_ROOT, provider_mode=args.provider_mode)
    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    else:
        print("Local AI evaluation")
        print(f"Provider mode: {report.provider_mode}")
        print(f"Status: {'OK' if report.ok else 'FAILED'}")
        for result in report.results:
            print(f"[{'OK' if result.passed else 'FAILED'}] {result.case_id}: {result.question}")
            print(f"  provider: {result.provider_name}")
            print(f"  sources: {', '.join(result.sources) if result.sources else '-'}")
            for failure in result.failures:
                print(f"  - {failure}")

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
