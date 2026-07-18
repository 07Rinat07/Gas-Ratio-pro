from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.calibration_package_trust_contract import (
    build_detached_signature,
    build_trust_key_record,
    build_trust_registry,
    detached_signature_fingerprint,
    validate_detached_signature_structure,
    validate_trust_registry,
    verify_detached_signature,
)
from services.calibration_package_trust_application_service import (
    CalibrationPackageTrustApplicationService,
    CalibrationPackageTrustDenied,
    CalibrationPackageTrustError,
)
from services.operator_calibration_package_application_service import OperatorCalibrationPackageApplicationService
from tests.calibration_package_trust_helpers import (
    approve_and_promote_to_production,
    build_trust_fixture,
)
from tests.operator_calibration_package_helpers import build_operator_package_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_detached_ed25519_signature_and_registry_are_deterministic() -> None:
    private_key = Ed25519PrivateKey.generate()
    registry = build_trust_registry(
        registry_id="registry-1",
        generated_at="2026-07-18T00:00:00+00:00",
        keys=[
            build_trust_key_record(
                key_id="key-1",
                public_key=private_key.public_key(),
                owner="Owner",
                organization_id="ORG",
                allowed_projects=["project-a"],
            )
        ],
    )
    assert validate_trust_registry(registry) == ()
    signature = build_detached_signature(
        private_key=private_key,
        package_fingerprint="a" * 64,
        key_id="key-1",
        project_id="project-a",
        signer_id="signer-1",
        signer_name="Owner",
        organization_id="ORG",
        signed_at="2026-07-18T00:00:00+00:00",
    )
    assert validate_detached_signature_structure(signature) == ()
    assert signature["signature_fingerprint"] == detached_signature_fingerprint(signature)
    assert verify_detached_signature(signature, public_key=private_key.public_key())
    tampered = dict(signature)
    tampered["project_id"] = "project-b"
    assert not verify_detached_signature(tampered, public_key=private_key.public_key())


def test_signature_review_and_controlled_promotion_to_production(tmp_path: Path) -> None:
    fixture = build_trust_fixture(tmp_path, ROOT)
    trust = fixture["trust"]
    package = fixture["package"]
    record = trust.import_detached_signature(json.dumps(fixture["signature"]).encode("utf-8"))
    assert record.package_fingerprint == package.package_fingerprint
    with pytest.raises(CalibrationPackageTrustDenied):
        trust.promote(package.package_fingerprint, target_environment="validation")
    trust.submit_review(
        package.package_fingerprint,
        reviewer_id="tech",
        reviewer_name="Technical reviewer",
        reviewer_role="technical_reviewer",
        decision="approve",
        comment="Accepted.",
    )
    validation = trust.promote(package.package_fingerprint, target_environment="validation")
    assert validation.source_environment == "development"
    assert validation.target_environment == "validation"
    with pytest.raises(CalibrationPackageTrustDenied):
        trust.promote(package.package_fingerprint, target_environment="production")
    trust.submit_review(
        package.package_fingerprint,
        reviewer_id="gov",
        reviewer_name="Governance reviewer",
        reviewer_role="data_governance_reviewer",
        decision="approve",
        comment="Production rights accepted.",
    )
    production = trust.promote(package.package_fingerprint, target_environment="production")
    assert production.target_environment == "production"
    decision = trust.assert_production_authorized(package.package_fingerprint)
    assert decision.passed
    assert decision.signature_fingerprint == record.signature_fingerprint
    assert decision.promotion_id == production.promotion_id


def test_rejection_revocation_and_expiry_block_trust(tmp_path: Path) -> None:
    fixture = build_trust_fixture(tmp_path, ROOT)
    trust = fixture["trust"]
    package = fixture["package"]
    trust.import_detached_signature(json.dumps(fixture["signature"]).encode("utf-8"))
    trust.submit_review(
        package.package_fingerprint,
        reviewer_id="tech",
        reviewer_name="Technical reviewer",
        reviewer_role="technical_reviewer",
        decision="reject",
        comment="Calibration evidence is incomplete.",
    )
    decision = trust.evaluate(package.package_fingerprint, requested_environment="validation")
    assert not decision.passed
    assert "review_rejected" in decision.reasons
    trust.submit_review(
        package.package_fingerprint,
        reviewer_id="tech",
        reviewer_name="Technical reviewer",
        reviewer_role="technical_reviewer",
        decision="approve",
        comment="Evidence corrected.",
    )
    trust.promote(package.package_fingerprint, target_environment="validation")
    trust.submit_review(
        package.package_fingerprint,
        reviewer_id="gov",
        reviewer_name="Governance reviewer",
        reviewer_role="data_governance_reviewer",
        decision="approve",
        comment="Rights accepted.",
    )
    trust.promote(package.package_fingerprint, target_environment="production")
    trust.revoke(
        target_type="package",
        target_id=package.package_fingerprint,
        revoked_by="governance-1",
        reviewer_role="data_governance_reviewer",
        reason="Operator withdrew the dataset.",
    )
    revoked = trust.evaluate(package.package_fingerprint, requested_environment="production", final_report=True)
    assert not revoked.passed
    assert "package_revoked" in revoked.reasons


def test_expiry_monitor_reports_key_signature_and_rights(tmp_path: Path) -> None:
    future = datetime.now(timezone.utc) + timedelta(days=5)
    fixture = build_trust_fixture(tmp_path, ROOT, valid_until=future.isoformat())
    signature = dict(fixture["signature"])
    # Re-sign with a near-term signature expiry.
    signature = build_detached_signature(
        private_key=fixture["private_key"],
        package_fingerprint=fixture["package"].package_fingerprint,
        key_id=fixture["key_id"],
        project_id="project-a",
        signer_id="signer-1",
        signer_name="Operator signer",
        organization_id="ORG-1",
        expires_at=(datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
    )
    fixture["trust"].import_detached_signature(json.dumps(signature).encode("utf-8"))
    report = fixture["trust"].monitor_expiry(warning_window_days=10)
    assert report.expiring_count >= 2
    assert any(item.item_type == "key" and item.status == "expiring" for item in report.items)
    assert any(item.item_type == "signature" and item.status == "expiring" for item in report.items)


def test_lineage_parent_must_exist_and_cycles_are_rejected(tmp_path: Path) -> None:
    fixture = build_trust_fixture(tmp_path, ROOT)
    bad = build_detached_signature(
        private_key=fixture["private_key"],
        package_fingerprint=fixture["package"].package_fingerprint,
        key_id=fixture["key_id"],
        project_id="project-a",
        signer_id="signer-1",
        signer_name="Operator signer",
        organization_id="ORG-1",
        parent_package_fingerprint="b" * 64,
        lineage_relation="supersedes",
        lineage_reason="New calibration version.",
    )
    with pytest.raises(CalibrationPackageTrustError, match="lineage parent"):
        fixture["trust"].import_detached_signature(json.dumps(bad).encode("utf-8"))


def test_signature_cannot_cross_project_scope(tmp_path: Path) -> None:
    fixture = build_trust_fixture(tmp_path, ROOT, project_id="project-a")
    other_operator = OperatorCalibrationPackageApplicationService(
        projects_root=fixture["projects_root"],
        application_root=ROOT,
        project_id="project-b",
    )
    other = other_operator.import_package(build_operator_package_bytes(ROOT, project_id="project-b"))
    other_trust = CalibrationPackageTrustApplicationService(
        projects_root=fixture["projects_root"],
        application_root=ROOT,
        project_id="project-b",
        registry_path=fixture["registry_path"],
    )
    signature = build_detached_signature(
        private_key=fixture["private_key"],
        package_fingerprint=other.package_fingerprint,
        key_id=fixture["key_id"],
        project_id="project-a",
        signer_id="signer-1",
        signer_name="Operator signer",
        organization_id="ORG-1",
    )
    with pytest.raises(CalibrationPackageTrustError):
        other_trust.import_detached_signature(json.dumps(signature).encode("utf-8"))


def test_strict_operator_boundary_blocks_activation_until_production_promotion(tmp_path: Path) -> None:
    fixture = build_trust_fixture(tmp_path, ROOT)
    strict = OperatorCalibrationPackageApplicationService(
        projects_root=fixture["projects_root"],
        application_root=ROOT,
        project_id="project-a",
        trust_service=fixture["trust"],
        require_production_trust=True,
    )
    package = fixture["package"]
    with pytest.raises(CalibrationPackageTrustDenied):
        strict.activate_package(package.package_fingerprint)
    approve_and_promote_to_production(fixture)
    strict.activate_package(package.package_fingerprint)
    authorization = strict.issue_authorization_package(
        ["petrophysics.sw_archie"],
        final_report=True,
    )
    assert authorization.passed
    assert authorization.trust_decision_id.startswith("trust-")
    assert authorization.trust_signature_fingerprint
    assert authorization.trust_promotion_id.startswith("prom-")


def test_environment_state_tampering_cannot_grant_or_preserve_production_trust(tmp_path: Path) -> None:
    fixture = build_trust_fixture(tmp_path, ROOT)
    approve_and_promote_to_production(fixture)
    trust = fixture["trust"]
    package = fixture["package"]
    state_path = trust.environments_root / f"{package.package_fingerprint}.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["promotion_id"] = "prom-forged-state"
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    decision = trust.evaluate(
        package.package_fingerprint,
        requested_environment="production",
        final_report=True,
    )
    assert not decision.passed
    assert "production_promotion_evidence_missing_or_mismatched" in decision.reasons


def test_key_revocation_blocks_existing_production_package(tmp_path: Path) -> None:
    fixture = build_trust_fixture(tmp_path, ROOT)
    approve_and_promote_to_production(fixture)
    trust = fixture["trust"]
    package = fixture["package"]
    trust.revoke(
        target_type="key",
        target_id=fixture["key_id"],
        revoked_by="security-admin",
        reviewer_role="data_governance_reviewer",
        reason="Signing key compromised.",
    )
    decision = trust.evaluate(
        package.package_fingerprint,
        requested_environment="production",
        final_report=True,
    )
    assert not decision.passed
    assert {"trusted_detached_signature_missing", "trusted_key_missing"}.issubset(decision.reasons)
