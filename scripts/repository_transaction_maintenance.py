"""Inspect and maintain repository transaction journals without loading the UI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.repository_io import AtomicJsonStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Repository root containing transaction folders")
    parser.add_argument("--repository", default="maintenance", help="Telemetry repository name")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="List active and quarantined transaction journals")
    inspect_parser = subparsers.add_parser("inspect", help="Inspect one transaction journal")
    inspect_parser.add_argument("transaction_id")
    recover_parser = subparsers.add_parser("recover", help="Recover one safe quarantined transaction")
    recover_parser.add_argument("transaction_id")
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean old valid committed journals")
    cleanup_parser.add_argument("--older-than-days", type=float, default=30.0)
    cleanup_parser.add_argument("--apply", action="store_true", help="Apply cleanup; default is dry run")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    store = AtomicJsonStore(repository=args.repository)
    if args.command == "list":
        result = store.list_transaction_journals(root)
    elif args.command == "inspect":
        rows = store.list_transaction_journals(root)
        matches = [row for row in rows if row["transaction_id"] == args.transaction_id]
        if len(matches) != 1:
            raise SystemExit(f"transaction not uniquely found: {args.transaction_id}")
        result = matches[0]
    elif args.command == "recover":
        result = store.recover_quarantined_transaction(root, args.transaction_id)
    else:
        result = store.cleanup_transaction_journals(
            root,
            older_than_seconds=max(0.0, args.older_than_days) * 86400.0,
            dry_run=not args.apply,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
