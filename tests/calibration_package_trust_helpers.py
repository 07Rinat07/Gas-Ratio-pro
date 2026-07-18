from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.calibration_package_trust_contract import (
    build_detached_signature,
    build_trust_key_record,
    build_trust_registry,
)
from services.calibration_package_trust_application_service import CalibrationPackageTrustApplicationService
from services.operator_calibration_package_application_service import OperatorCalibrationPackageApplicationService
from tests.operator_calibration_package_helpers import build_operator_package_bytes


def build_trust_fixture(
    tmp_path: Path,
    application_root: Path,
    *,
    project_id: str = "project-a",
    key_id: str = "operator-key-1",
    organization_id: str = "ORG-1",
    valid_until: str = "",
) -> dict[str, Any]:
    projects_root = tmp_path / "projects"
    operator = OperatorCalibrationPackageApplicationService(
        projects_root=projects_root,
        application_root=application_root,
        project_id=project_id,
    )
    package = operator.import_package(
        build_operator_package_bytes(application_root, project_id=project_id)
    )
    private_key = Ed25519PrivateKey.generate()
    registry = build_trust_registry(
        registry_id="test-calibration-trust",
        keys=[
            build_trust_key_record(
                key_id=key_id,
                public_key=private_key.public_key(),
                owner="Operator signer",
                organization_id=organization_id,
                allowed_projects=[project_id],
                allowed_environments=["validation", "production"],
                valid_until=valid_until or None,
            )
        ],
    )
    registry_path = tmp_path / "trust_registry.json"
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    trust = CalibrationPackageTrustApplicationService(
        projects_root=projects_root,
        application_root=application_root,
        project_id=project_id,
        registry_path=registry_path,
    )
    signature = build_detached_signature(
        private_key=private_key,
        package_fingerprint=package.package_fingerprint,
        key_id=key_id,
        project_id=project_id,
        signer_id="signer-1",
        signer_name="Operator signer",
        organization_id=organization_id,
    )
    return {
        "projects_root": projects_root,
        "operator": operator,
        "package": package,
        "private_key": private_key,
        "registry": registry,
        "registry_path": registry_path,
        "trust": trust,
        "signature": signature,
        "key_id": key_id,
    }


def approve_and_promote_to_production(fixture: dict[str, Any]) -> None:
    trust = fixture["trust"]
    package = fixture["package"]
    trust.import_detached_signature(json.dumps(fixture["signature"]).encode("utf-8"))
    trust.submit_review(
        package.package_fingerprint,
        reviewer_id="technical-1",
        reviewer_name="Technical reviewer",
        reviewer_role="technical_reviewer",
        decision="approve",
        comment="Numerical and lineage evidence accepted.",
    )
    trust.promote(package.package_fingerprint, target_environment="validation")
    trust.submit_review(
        package.package_fingerprint,
        reviewer_id="governance-1",
        reviewer_name="Data governance reviewer",
        reviewer_role="data_governance_reviewer",
        decision="approve",
        comment="Rights, provenance, and production use accepted.",
    )
    trust.promote(package.package_fingerprint, target_environment="production")
