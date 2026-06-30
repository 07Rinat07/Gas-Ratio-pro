from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.preflight import run_preflight


def main() -> int:
    parser = argparse.ArgumentParser(description="Gas Ratio Interpreter preflight check")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    report = run_preflight(ROOT_DIR)
    if args.json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    else:
        print("Gas Ratio Interpreter preflight")
        print(f"Status: {'OK' if report.ok else 'FAILED'}")
        for check in report.checks:
            print(f"[{check.status.upper()}] {check.name}: {check.message}")

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
