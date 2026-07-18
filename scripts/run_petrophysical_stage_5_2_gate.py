#!/usr/bin/env python3
"""Run Stage 5.2 import, comparison and project authorization acceptance."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_operator_calibration_package import build_archive  # noqa: E402
from services.operator_calibration_package_application_service import (  # noqa: E402
    OperatorCalibrationPackageApplicationService,
)
from services.petrophysical_validation_application_service import (  # noqa: E402
    PetrophysicalValidationApplicationService,
)

EVIDENCE_SCHEMA = "gas-ratio-pro/petrophysical-stage-5.2-evidence/v1"


def _operator_contracts() -> tuple[dict, dict]:
    registry = json.loads((ROOT / "config/petrophysical_field_calibration_registry_v225_10.json").read_text(encoding="utf-8"))
    dataset = json.loads((ROOT / "data/validation/petrophysics/petrophysical_field_calibration_cases_v225_10.json").read_text(encoding="utf-8"))
    registry = deepcopy(registry)
    dataset = deepcopy(dataset)
    registry["version"] = "v225.11-acceptance"
    dataset["version"] = "v225.11-acceptance"
    calibration_id = "grp_stage_5_2_operator_acceptance"
    for record in dataset["calibration_sets"]:
        record.update(
            {
                "calibration_id": calibration_id,
                "title": "Gas Ratio Pro Stage 5.2 operator-owned acceptance dataset",
                "owner": "Gas Ratio Pro acceptance operator",
                "legal_status": "operator_owned",
                "license_id": "GRP-STAGE-5.2-ACCEPTANCE",
                "redistribution_allowed": False,
                "source_type": "operator_acceptance_surrogate",
                "source_note": "Project-owned synthetic values wrapped as operator-local data for Stage 5.2 acceptance.",
            }
        )
    for case in dataset["cases"]:
        case["calibration_id"] = calibration_id
    return registry, dataset


def run_gate(output: Path) -> dict:
    registry, dataset = _operator_contracts()
    validation = PetrophysicalValidationApplicationService(root=ROOT).run_gate()
    eligible = tuple(item.method_id for item in validation.methods if item.final_report_eligible)
    with tempfile.TemporaryDirectory(prefix="grp-stage-5-2-") as temporary:
        projects_root = Path(temporary) / "projects"
        service = OperatorCalibrationPackageApplicationService(
            projects_root=projects_root,
            application_root=ROOT,
            project_id="stage-5-2-acceptance",
        )
        package_bytes = build_archive(
            registry=registry,
            dataset=dataset,
            package_id="grp-stage-5-2-acceptance",
            version="1.0.0",
            project_ids=("stage-5-2-acceptance",),
            operator_name="Gas Ratio Pro acceptance operator",
            organization_id="GRP-ACCEPTANCE",
            owner="Gas Ratio Pro acceptance operator",
            legal_status="operator_owned",
            legal_basis="Project-owned synthetic acceptance data",
            data_classification="internal",
            final_report_use_allowed=True,
            redistribution_allowed=False,
            notes="Release acceptance package; no third-party field data.",
        )
        imported = service.import_package(package_bytes)
        active = service.activate_package(imported.package_fingerprint)
        comparison = service.compare(active.package_fingerprint)
        authorization = service.issue_authorization_package(eligible)
        authorization.assert_authorized()
        evidence = {
            "schema": EVIDENCE_SCHEMA,
            "project_id": "stage-5-2-acceptance",
            "import": imported.to_dict(),
            "active_package_fingerprint": active.package_fingerprint,
            "comparison": comparison.to_dict(),
            "authorization": authorization.to_dict(),
            "summary": {
                "imported_packages": 1,
                "compared_methods": len(comparison.methods),
                "authorized_methods": sum(item.authorized for item in authorization.methods),
                "final_report_eligible_methods": len(eligible),
                "passed": comparison.passed and authorization.passed,
            },
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return evidence


def main() -> int:
    output = ROOT / "artifacts" / "validation" / "petrophysical_operator_calibration_v225_11.json"
    evidence = run_gate(output)
    summary = evidence["summary"]
    print(f"imported_packages: {summary['imported_packages']}")
    print(f"compared_methods: {summary['compared_methods']}")
    print(f"authorized_methods: {summary['authorized_methods']}")
    print(f"passed: {summary['passed']}")
    print(f"evidence: {output}")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
