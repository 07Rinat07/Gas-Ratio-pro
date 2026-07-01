from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.training_dataset import default_ai_training_pack_dir, write_ai_training_pack  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a safe local AI training/evaluation pack from approved project knowledge."
    )
    parser.add_argument(
        "--output-dir",
        default=str(default_ai_training_pack_dir()),
        help="Directory for generated JSONL files.",
    )
    parser.add_argument(
        "--include-draft",
        action="store_true",
        help="Include draft Q/A examples. Approved/reference examples are exported by default.",
    )
    parser.add_argument("--json", action="store_true", help="Print report as JSON.")
    return parser


def _print_report(report: dict) -> None:
    manifest = report["manifest"]
    counts = manifest["counts"]
    print("AI training pack exported")
    print(f"Output: {report['output_dir']}")
    print(f"Train records: {counts['train']} -> {report['train_path']}")
    print(f"Eval records: {counts['eval']} -> {report['eval_path']}")
    print(f"Manifest: {report['manifest_path']}")
    print("Safety: raw user tables are not allowed in this pack.")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    report = write_ai_training_pack(
        output_dir=args.output_dir,
        root=PROJECT_ROOT,
        include_draft=args.include_draft,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
