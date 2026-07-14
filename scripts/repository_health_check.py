"""Scan repository JSON health and optionally quarantine one explicit target."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.repository_health import RepositoryHealthService


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--max-files", type=int, default=5000)
    parser.add_argument("--apply", metavar="ACTION_ID", help="Apply one action from a fresh repair plan")
    args = parser.parse_args()
    service = RepositoryHealthService(args.root, max_files=args.max_files, scan_ttl_seconds=0)
    if args.apply:
        result = service.apply_repair(args.apply)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    snapshot = service.scan(force=True).to_dict()
    print(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if snapshot["healthy"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
