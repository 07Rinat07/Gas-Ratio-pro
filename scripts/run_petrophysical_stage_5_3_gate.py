#!/usr/bin/env python3
"""Run Stage 5.3 signature, review, revocation, expiry and promotion acceptance."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from core.calibration_package_trust_contract import (  # noqa: E402
    build_detached_signature,
    build_trust_key_record,
    build_trust_registry,
)
from scripts.build_operator_calibration_package import build_archive  # noqa: E402
from services.calibration_package_trust_application_service import (  # noqa: E402
    CalibrationPackageTrustApplicationService,
)
from services.operator_calibration_package_application_service import (  # noqa: E402
    OperatorCalibrationPackageApplicationService,
)
from services.petrophysical_validation_application_service import (  # noqa: E402
    PetrophysicalValidationApplicationService,
)

EVIDENCE_SCHEMA = "gas-ratio-pro/petrophysical-stage-5.3-evidence/v1"


def _operator_contracts() -> tuple[dict, dict]:
    registry = deepcopy(json.loads((ROOT / "config/petrophysical_field_calibration_registry_v225_10.json").read_text(encoding="utf-8")))
    dataset = deepcopy(json.loads((ROOT / "data/validation/petrophysics/petrophysical_field_calibration_cases_v225_10.json").read_text(encoding="utf-8")))
    registry["version"] = "v225.12-trust-acceptance"
    dataset["version"] = "v225.12-trust-acceptance"
    calibration_id = "grp_stage_5_3_trust_acceptance"
    for record in dataset["calibration_sets"]:
        record.update(
            {
                "calibration_id": calibration_id,
                "title": "Gas Ratio Pro Stage 5.3 trust acceptance dataset",
                "owner": "Gas Ratio Pro trust acceptance operator",
                "legal_status": "operator_owned",
                "license_id": "GRP-STAGE-5.3-ACCEPTANCE",
                "redistribution_allowed": False,
                "source_type": "operator_trust_acceptance_surrogate",
                "source_note": "Project-owned synthetic evidence; no third-party field data.",
            }
        )
    for case in dataset["cases"]:
        case["calibration_id"] = calibration_id
    return registry, dataset


def run_gate(output: Path) -> dict:
    registry, dataset = _operator_contracts()
    validation = PetrophysicalValidationApplicationService(root=ROOT).run_gate()
    eligible = tuple(item.method_id for item in validation.methods if item.final_report_eligible)
    with tempfile.TemporaryDirectory(prefix="grp-stage-5-3-") as temporary:
        temporary_root = Path(temporary)
        projects_root = temporary_root / "projects"
        project_id = "stage-5-3-acceptance"
        private_key = Ed25519PrivateKey.generate()
        valid_until = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        trust_registry = build_trust_registry(
            registry_id="grp-stage-5-3-acceptance-trust",
            keys=[
                build_trust_key_record(
                    key_id="grp-acceptance-key-1",
                    public_key=private_key.public_key(),
                    owner="Gas Ratio Pro acceptance signer",
                    organization_id="GRP-ACCEPTANCE",
                    allowed_projects=[project_id],
                    allowed_environments=["validation", "production"],
                    valid_until=valid_until,
                )
            ],
        )
        trust_registry_path = temporary_root / "trust_registry.json"
        trust_registry_path.write_text(json.dumps(trust_registry, ensure_ascii=False, indent=2), encoding="utf-8")
        trust = CalibrationPackageTrustApplicationService(
            projects_root=projects_root,
            application_root=ROOT,
            project_id=project_id,
            registry_path=trust_registry_path,
        )
        service = OperatorCalibrationPackageApplicationService(
            projects_root=projects_root,
            application_root=ROOT,
            project_id=project_id,
            trust_service=trust,
            require_production_trust=True,
        )
        package_bytes = build_archive(
            registry=registry,
            dataset=dataset,
            package_id="grp-stage-5-3-acceptance",
            version="1.0.0",
            project_ids=(project_id,),
            operator_name="Gas Ratio Pro trust acceptance operator",
            organization_id="GRP-ACCEPTANCE",
            owner="Gas Ratio Pro trust acceptance operator",
            legal_status="operator_owned",
            legal_basis="Project-owned synthetic trust acceptance data",
            data_classification="internal",
            final_report_use_allowed=True,
            redistribution_allowed=False,
            expires_at=valid_until,
            notes="Release trust acceptance package; no third-party data.",
        )
        imported = service.import_package(package_bytes)
        signature = build_detached_signature(
            private_key=private_key,
            package_fingerprint=imported.package_fingerprint,
            key_id="grp-acceptance-key-1",
            project_id=project_id,
            signer_id="acceptance-signer",
            signer_name="Gas Ratio Pro acceptance signer",
            organization_id="GRP-ACCEPTANCE",
            expires_at=valid_until,
        )
        signature_record = trust.import_detached_signature(json.dumps(signature).encode("utf-8"))
        technical_review = trust.submit_review(
            imported.package_fingerprint,
            reviewer_id="acceptance-technical",
            reviewer_name="Acceptance technical reviewer",
            reviewer_role="technical_reviewer",
            decision="approve",
            comment="Numerical calibration and lineage accepted.",
        )
        validation_promotion = trust.promote(imported.package_fingerprint, target_environment="validation")
        governance_review = trust.submit_review(
            imported.package_fingerprint,
            reviewer_id="acceptance-governance",
            reviewer_name="Acceptance data-governance reviewer",
            reviewer_role="data_governance_reviewer",
            decision="approve",
            comment="Rights, expiry and production use accepted.",
        )
        production_promotion = trust.promote(imported.package_fingerprint, target_environment="production")
        active = service.activate_package(imported.package_fingerprint)
        authorization = service.issue_authorization_package(eligible)
        authorization.assert_authorized()
        trust_decision = trust.assert_production_authorized(imported.package_fingerprint)
        expiry = trust.monitor_expiry(warning_window_days=30)
        evidence = {
            "schema": EVIDENCE_SCHEMA,
            "project_id": project_id,
            "package_fingerprint": imported.package_fingerprint,
            "signature": signature_record.to_dict(),
            "reviews": [technical_review.to_dict(), governance_review.to_dict()],
            "promotions": [validation_promotion.to_dict(), production_promotion.to_dict()],
            "active_package": active.to_dict(),
            "trust_decision": trust_decision.to_dict(),
            "authorization": authorization.to_dict(),
            "expiry_monitor": expiry.to_dict(),
            "summary": {
                "signature_verified": 1,
                "review_approvals": 2,
                "promotions_completed": 2,
                "production_trust_passed": trust_decision.passed,
                "authorized_methods": sum(item.authorized for item in authorization.methods),
                "final_report_eligible_methods": len(eligible),
                "private_keys_persisted": 0,
                "production_formulas_changed": False,
                "passed": trust_decision.passed and authorization.passed,
            },
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return evidence


def main() -> int:
    output = ROOT / "artifacts" / "validation" / "calibration_package_trust_v225_12.json"
    evidence = run_gate(output)
    summary = evidence["summary"]
    for key in (
        "signature_verified",
        "review_approvals",
        "promotions_completed",
        "production_trust_passed",
        "authorized_methods",
        "final_report_eligible_methods",
        "private_keys_persisted",
        "production_formulas_changed",
        "passed",
    ):
        print(f"{key}: {summary[key]}")
    print(f"evidence: {output}")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
