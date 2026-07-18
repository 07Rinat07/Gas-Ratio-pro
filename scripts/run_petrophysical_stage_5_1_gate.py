#!/usr/bin/env python3
"""Run Stage 5.1 calibration and final-report authorization gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.petrophysical_validation_contract import load_petrophysical_method_registry
from services.petrophysical_calibration_application_service import PetrophysicalCalibrationApplicationService
from services.petrophysical_report_authorization_application_service import PetrophysicalReportAuthorizationApplicationService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration-output", default="artifacts/validation/petrophysical_calibration_v225_10.json")
    parser.add_argument("--authorization-output", default="artifacts/validation/petrophysical_report_authorization_v225_10.json")
    args = parser.parse_args()

    calibration_service = PetrophysicalCalibrationApplicationService(root=ROOT)
    calibration = calibration_service.write_evidence(args.calibration_output)
    calibration.assert_passed()

    registry = load_petrophysical_method_registry(ROOT / "config/petrophysical_method_registry_v225_9.json")
    eligible = tuple(
        item["method_id"] for item in registry["methods"]
        if item["report_policy"] != "blocked_final_report"
    )
    authorization_service = PetrophysicalReportAuthorizationApplicationService(
        root=ROOT,
        validation_service=calibration_service.validation_service,
        calibration_service=calibration_service,
    )
    authorization = authorization_service.write_evidence(
        eligible,
        args.authorization_output,
        final_report=True,
    )
    authorization.assert_authorized()
    print(json.dumps({
        "calibration_gate_id": calibration.gate_id,
        "calibrated": calibration.calibrated_method_count,
        "final_report_calibrated": calibration.final_report_calibrated_count,
        "authorization_id": authorization.authorization_id,
        "authorized_methods": len(authorization.method_ids),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
