#!/usr/bin/env python3
"""Run the Stage 5 petrophysical validation gate and persist evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.petrophysical_validation_application_service import (  # noqa: E402
    PetrophysicalValidationApplicationService,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="artifacts/validation/petrophysical_validation_v225_9.json",
        help="Evidence path relative to the project root.",
    )
    args = parser.parse_args()
    service = PetrophysicalValidationApplicationService(root=ROOT)
    report = service.write_evidence(args.output)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
