"""Stage 5.3 trust, review, revocation and promotion boundary.

The service never modifies an operator calibration package. It verifies a
detached Ed25519 signature against an application trust registry and stores
append-only review, revocation, lineage and environment-promotion evidence in
the project repository.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.calibration_package_trust_contract import (
    CALIBRATION_EXPIRY_REPORT_SCHEMA,
    CALIBRATION_PROMOTION_RECORD_SCHEMA,
    CALIBRATION_REVIEW_DECISION_SCHEMA,
    CALIBRATION_REVOCATION_SCHEMA,
    CALIBRATION_TRUST_DECISION_SCHEMA,
    ENVIRONMENTS,
    REVIEW_DECISIONS,
    REVIEW_ROLES,
    REVOCATION_TARGETS,
    SIGNING_PURPOSE,
    canonical_json_bytes,
    detached_signature_fingerprint,
    immutable_record_fingerprint,
    load_public_key_base64,
    parse_utc_datetime,
    sha256_hex,
    trust_registry_fingerprint,
    utc_now_iso,
    validate_detached_signature_structure,
    validate_trust_registry,
    verify_detached_signature,
)
from core.operator_calibration_package_contract import (
    PACKAGE_MANIFEST_NAME,
    operator_package_fingerprint,
    safe_package_component,
)
from projects.repository import safe_project_id


class CalibrationPackageTrustError(ValueError):
    """Raised when trust evidence or a promotion violates Stage 5.3."""


class CalibrationPackageTrustDenied(PermissionError):
    """Raised when a package is not trusted for the requested environment."""


@dataclass(frozen=True, slots=True)
class DetachedSignatureRecord:
    package_fingerprint: str
    signature_fingerprint: str
    key_id: str
    signer_id: str
    signer_name: str
    organization_id: str
    signed_at: str
    expires_at: str
    parent_package_fingerprint: str
    lineage_relation: str
    storage_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReviewDecisionRecord:
    schema: str
    project_id: str
    package_fingerprint: str
    reviewer_id: str
    reviewer_name: str
    reviewer_role: str
    decision: str
    comment: str
    decided_at: str
    previous_decision_fingerprint: str
    decision_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RevocationRecord:
    schema: str
    project_id: str
    target_type: str
    target_id: str
    revoked_by: str
    reviewer_role: str
    reason: str
    effective_at: str
    recorded_at: str
    revocation_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PromotionRecord:
    schema: str
    project_id: str
    package_fingerprint: str
    source_environment: str
    target_environment: str
    promoted_at: str
    trust_decision_id: str
    signature_fingerprint: str
    key_id: str
    review_decision_fingerprints: tuple[str, ...]
    parent_package_fingerprint: str
    promotion_id: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["review_decision_fingerprints"] = list(self.review_decision_fingerprints)
        return payload


@dataclass(frozen=True, slots=True)
class CalibrationPackageTrustDecision:
    schema: str
    generated_at: str
    decision_id: str
    project_id: str
    package_fingerprint: str
    requested_environment: str
    current_environment: str
    final_report: bool
    passed: bool
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    signature_fingerprint: str
    key_id: str
    trust_registry_fingerprint: str
    review_decision_fingerprints: tuple[str, ...]
    promotion_id: str
    parent_package_fingerprint: str
    rights_expires_at: str
    signature_expires_at: str
    key_valid_until: str

    @property
    def authorization_gate_ids(self) -> tuple[str, ...]:
        return tuple(
            value
            for value in (
                self.decision_id,
                self.signature_fingerprint,
                self.promotion_id,
            )
            if value
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reasons"] = list(self.reasons)
        payload["warnings"] = list(self.warnings)
        payload["review_decision_fingerprints"] = list(self.review_decision_fingerprints)
        payload["authorization_gate_ids"] = list(self.authorization_gate_ids)
        return payload

    def assert_trusted(self) -> None:
        if not self.passed:
            raise CalibrationPackageTrustDenied(
                "Calibration package trust decision failed: " + ", ".join(self.reasons)
            )


@dataclass(frozen=True, slots=True)
class ExpiryMonitorItem:
    item_type: str
    item_id: str
    package_fingerprint: str
    expires_at: str
    status: str
    days_remaining: int | None


@dataclass(frozen=True, slots=True)
class CalibrationPackageExpiryReport:
    schema: str
    generated_at: str
    project_id: str
    warning_window_days: int
    passed: bool
    expired_count: int
    expiring_count: int
    items: tuple[ExpiryMonitorItem, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["items"] = [asdict(item) for item in self.items]
        return payload


class CalibrationPackageTrustApplicationService:
    """Own the project-scoped trust and review workflow for Stage 5.3."""

    INDEX_SCHEMA = "gas-ratio-pro/calibration-trust-state-index/v1"
    ENVIRONMENT_STATE_SCHEMA = "gas-ratio-pro/calibration-environment-state/v1"
    REQUIRED_REVIEWS = {
        "development": (),
        "validation": ("technical_reviewer",),
        "production": ("technical_reviewer", "data_governance_reviewer"),
    }

    def __init__(
        self,
        *,
        projects_root: Path | str,
        application_root: Path | str,
        project_id: str,
        registry_path: Path | str | None = None,
    ) -> None:
        self.projects_root = Path(projects_root).resolve()
        self.application_root = Path(application_root).resolve()
        self.project_id = safe_project_id(str(project_id))
        self.registry_path = (
            Path(registry_path).resolve()
            if registry_path is not None
            else self.application_root / "config" / "calibration_trust_registry_v225_12.json"
        )

    @property
    def project_root(self) -> Path:
        return self.projects_root / self.project_id

    @property
    def operator_repository_root(self) -> Path:
        return self.project_root / "petrophysics" / "operator_calibration"

    @property
    def trust_root(self) -> Path:
        return self.operator_repository_root / "trust"

    @property
    def signatures_root(self) -> Path:
        return self.trust_root / "signatures"

    @property
    def reviews_root(self) -> Path:
        return self.trust_root / "reviews"

    @property
    def revocations_root(self) -> Path:
        return self.trust_root / "revocations"

    @property
    def promotions_root(self) -> Path:
        return self.trust_root / "promotions"

    @property
    def environments_root(self) -> Path:
        return self.trust_root / "environments"

    def load_registry(self) -> dict[str, Any]:
        try:
            registry = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise CalibrationPackageTrustError(f"trust registry not found: {self.registry_path}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise CalibrationPackageTrustError("trust registry is unreadable or invalid JSON") from exc
        if not isinstance(registry, dict):
            raise CalibrationPackageTrustError("trust registry root must be an object")
        errors = validate_trust_registry(registry)
        if errors:
            raise CalibrationPackageTrustError("; ".join(errors))
        return registry

    def import_detached_signature(self, source: bytes | bytearray | Path | str) -> DetachedSignatureRecord:
        envelope = self._read_json_source(source, label="detached signature")
        errors = list(validate_detached_signature_structure(envelope))
        package_fingerprint = str(envelope.get("package_fingerprint", "")).strip().lower()
        package = self._package_entry(package_fingerprint)
        if str(envelope.get("project_id", "")).strip() != self.project_id:
            errors.append("detached signature belongs to another project")
        if package_fingerprint != str(package.get("package_fingerprint", "")).lower():
            errors.append("detached signature package fingerprint does not match the stored package")
        registry = self.load_registry()
        key = self._key_record(registry, str(envelope.get("key_id", "")))
        if key is None:
            errors.append("signature key is not present in the trust registry")
        elif not self._key_scope_allows(key, environment="validation", at=self._utc_now_dt()):
            errors.append("signature key is not active for this project and validation environment")
        elif not verify_detached_signature(envelope, public_key=load_public_key_base64(key.get("public_key_base64"))):
            errors.append("detached Ed25519 signature verification failed")
        if key is not None:
            signer = envelope.get("signer", {})
            if str(signer.get("organization_id", "")) != str(key.get("organization_id", "")):
                errors.append("signature signer organization does not match the trusted key owner")
        expires_at = parse_utc_datetime(envelope.get("expires_at"), field="expires_at")
        if expires_at is not None and expires_at <= self._utc_now_dt():
            errors.append("detached signature has expired")
        lineage = envelope.get("lineage", {})
        parent = str(lineage.get("parent_package_fingerprint", "")).strip().lower()
        if parent:
            try:
                self._package_entry(parent)
            except KeyError:
                errors.append("lineage parent package is not imported in this project")
            if self._lineage_would_cycle(package_fingerprint, parent):
                errors.append("package lineage would create a cycle")
        existing_parents = {
            item.parent_package_fingerprint
            for item in self.list_signatures(package_fingerprint)
        }
        if existing_parents and parent not in existing_parents:
            errors.append("detached signatures for one package cannot declare conflicting lineage parents")
        if errors:
            raise CalibrationPackageTrustError("; ".join(dict.fromkeys(errors)))
        signature_fingerprint = detached_signature_fingerprint(envelope)
        destination = self.signatures_root / package_fingerprint / f"{signature_fingerprint}.json"
        if destination.exists():
            existing = json.loads(destination.read_text(encoding="utf-8"))
            if existing != envelope:
                raise CalibrationPackageTrustError("signature fingerprint is already stored with different content")
        else:
            self._atomic_write_json(destination, envelope)
        signer = envelope["signer"]
        return DetachedSignatureRecord(
            package_fingerprint=package_fingerprint,
            signature_fingerprint=signature_fingerprint,
            key_id=str(envelope["key_id"]),
            signer_id=str(signer["signer_id"]),
            signer_name=str(signer["name"]),
            organization_id=str(signer["organization_id"]),
            signed_at=str(envelope["signed_at"]),
            expires_at=str(envelope.get("expires_at", "")),
            parent_package_fingerprint=parent,
            lineage_relation=str(lineage.get("relation", "root")),
            storage_path=destination.relative_to(self.project_root).as_posix(),
        )

    def list_signatures(self, package_fingerprint: str) -> tuple[DetachedSignatureRecord, ...]:
        clean = self._clean_fingerprint(package_fingerprint)
        root = self.signatures_root / clean
        records: list[DetachedSignatureRecord] = []
        if not root.exists():
            return ()
        for path in sorted(root.glob("*.json")):
            try:
                envelope = json.loads(path.read_text(encoding="utf-8"))
                if validate_detached_signature_structure(envelope):
                    continue
                signer = envelope["signer"]
                lineage = envelope["lineage"]
                records.append(
                    DetachedSignatureRecord(
                        package_fingerprint=clean,
                        signature_fingerprint=str(envelope["signature_fingerprint"]),
                        key_id=str(envelope["key_id"]),
                        signer_id=str(signer["signer_id"]),
                        signer_name=str(signer["name"]),
                        organization_id=str(signer["organization_id"]),
                        signed_at=str(envelope["signed_at"]),
                        expires_at=str(envelope.get("expires_at", "")),
                        parent_package_fingerprint=str(lineage.get("parent_package_fingerprint", "")),
                        lineage_relation=str(lineage.get("relation", "root")),
                        storage_path=path.relative_to(self.project_root).as_posix(),
                    )
                )
            except (OSError, json.JSONDecodeError, KeyError, TypeError):
                continue
        return tuple(sorted(records, key=lambda item: (item.signed_at, item.signature_fingerprint)))

    def submit_review(
        self,
        package_fingerprint: str,
        *,
        reviewer_id: str,
        reviewer_name: str,
        reviewer_role: str,
        decision: str,
        comment: str,
        decided_at: str | None = None,
    ) -> ReviewDecisionRecord:
        clean = self._clean_fingerprint(package_fingerprint)
        self._package_entry(clean)
        role = str(reviewer_role).strip()
        verdict = str(decision).strip()
        if role not in REVIEW_ROLES:
            raise CalibrationPackageTrustError(f"unsupported reviewer role: {role}")
        if verdict not in REVIEW_DECISIONS:
            raise CalibrationPackageTrustError(f"unsupported review decision: {verdict}")
        reviewer = safe_package_component(reviewer_id, field="reviewer_id")
        if not str(reviewer_name).strip():
            raise CalibrationPackageTrustError("reviewer_name is required")
        if not str(comment).strip():
            raise CalibrationPackageTrustError("review comment is required")
        previous = self._latest_review_by_reviewer(clean, reviewer, role)
        payload: dict[str, Any] = {
            "schema": CALIBRATION_REVIEW_DECISION_SCHEMA,
            "project_id": self.project_id,
            "package_fingerprint": clean,
            "reviewer_id": reviewer,
            "reviewer_name": str(reviewer_name).strip(),
            "reviewer_role": role,
            "decision": verdict,
            "comment": str(comment).strip(),
            "decided_at": decided_at or utc_now_iso(),
            "previous_decision_fingerprint": previous.decision_fingerprint if previous else "",
        }
        parse_utc_datetime(payload["decided_at"], field="decided_at", required=True)
        payload["decision_fingerprint"] = immutable_record_fingerprint(
            payload, fingerprint_field="decision_fingerprint"
        )
        destination = self.reviews_root / clean / f"{payload['decision_fingerprint']}.json"
        self._write_immutable_json(destination, payload, label="review decision")
        return self._review_from_dict(payload)

    def list_reviews(self, package_fingerprint: str, *, latest_only: bool = False) -> tuple[ReviewDecisionRecord, ...]:
        clean = self._clean_fingerprint(package_fingerprint)
        root = self.reviews_root / clean
        records: list[ReviewDecisionRecord] = []
        if root.exists():
            for path in sorted(root.glob("*.json")):
                try:
                    records.append(self._review_from_dict(json.loads(path.read_text(encoding="utf-8"))))
                except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
                    continue
        records.sort(key=lambda item: (item.decided_at, item.decision_fingerprint))
        if not latest_only:
            return tuple(records)
        grouped: dict[tuple[str, str], list[ReviewDecisionRecord]] = {}
        for item in records:
            grouped.setdefault((item.reviewer_id, item.reviewer_role), []).append(item)
        latest: list[ReviewDecisionRecord] = []
        for items in grouped.values():
            referenced = {item.previous_decision_fingerprint for item in items if item.previous_decision_fingerprint}
            terminal = [item for item in items if item.decision_fingerprint not in referenced]
            candidates = terminal or items
            latest.append(max(candidates, key=lambda item: (item.decided_at, item.decision_fingerprint)))
        return tuple(sorted(latest, key=lambda item: (item.reviewer_role, item.reviewer_id)))

    def revoke(
        self,
        *,
        target_type: str,
        target_id: str,
        revoked_by: str,
        reviewer_role: str,
        reason: str,
        effective_at: str | None = None,
    ) -> RevocationRecord:
        kind = str(target_type).strip()
        if kind not in REVOCATION_TARGETS:
            raise CalibrationPackageTrustError(f"unsupported revocation target: {kind}")
        role = str(reviewer_role).strip()
        if role not in REVIEW_ROLES:
            raise CalibrationPackageTrustError(f"unsupported reviewer role: {role}")
        if not str(reason).strip():
            raise CalibrationPackageTrustError("revocation reason is required")
        target = str(target_id).strip().lower()
        if kind == "package":
            self._package_entry(target)
        elif kind == "signature" and not self._signature_path_by_id(target):
            raise CalibrationPackageTrustError("signature revocation target does not exist")
        elif kind == "key" and self._key_record(self.load_registry(), target) is None:
            raise CalibrationPackageTrustError("key revocation target does not exist")
        payload: dict[str, Any] = {
            "schema": CALIBRATION_REVOCATION_SCHEMA,
            "project_id": self.project_id,
            "target_type": kind,
            "target_id": target,
            "revoked_by": str(revoked_by).strip(),
            "reviewer_role": role,
            "reason": str(reason).strip(),
            "effective_at": effective_at or utc_now_iso(),
            "recorded_at": utc_now_iso(),
        }
        parse_utc_datetime(payload["effective_at"], field="effective_at", required=True)
        payload["revocation_fingerprint"] = immutable_record_fingerprint(
            payload, fingerprint_field="revocation_fingerprint"
        )
        destination = self.revocations_root / kind / safe_package_component(target, field="target_id") / f"{payload['revocation_fingerprint']}.json"
        self._write_immutable_json(destination, payload, label="revocation")
        return self._revocation_from_dict(payload)

    def list_revocations(self, *, target_type: str | None = None, target_id: str | None = None) -> tuple[RevocationRecord, ...]:
        root = self.revocations_root
        if target_type:
            root = root / str(target_type)
        if target_id:
            root = root / safe_package_component(str(target_id).lower(), field="target_id")
        records: list[RevocationRecord] = []
        if root.exists():
            for path in sorted(root.rglob("*.json")):
                try:
                    records.append(self._revocation_from_dict(json.loads(path.read_text(encoding="utf-8"))))
                except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
                    continue
        return tuple(sorted(records, key=lambda item: (item.effective_at, item.revocation_fingerprint)))

    def current_environment(self, package_fingerprint: str) -> str:
        return str(self._environment_state(package_fingerprint).get("environment", "development"))

    def _environment_state(self, package_fingerprint: str) -> dict[str, Any]:
        clean = self._clean_fingerprint(package_fingerprint)
        path = self.environments_root / f"{clean}.json"
        default = {
            "schema": self.ENVIRONMENT_STATE_SCHEMA,
            "project_id": self.project_id,
            "package_fingerprint": clean,
            "environment": "development",
            "promotion_id": "",
        }
        if not path.exists():
            return default
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        if (
            payload.get("schema") != self.ENVIRONMENT_STATE_SCHEMA
            or payload.get("project_id") != self.project_id
            or payload.get("package_fingerprint") != clean
            or payload.get("environment") not in ENVIRONMENTS
        ):
            return default
        return dict(payload)

    def evaluate(
        self,
        package_fingerprint: str,
        *,
        requested_environment: str | None = None,
        final_report: bool = False,
        now: datetime | None = None,
    ) -> CalibrationPackageTrustDecision:
        clean = self._clean_fingerprint(package_fingerprint)
        package = self._package_entry(clean)
        environment_state = self._environment_state(clean)
        current = str(environment_state.get("environment", "development"))
        requested = str(requested_environment or current)
        if requested not in ENVIRONMENTS:
            raise CalibrationPackageTrustError(f"unsupported project environment: {requested}")
        reference_time = (now or self._utc_now_dt()).astimezone(timezone.utc)
        reasons: list[str] = []
        warnings: list[str] = []
        registry = self.load_registry()
        registry_fp = trust_registry_fingerprint(registry)
        manifest = self._load_package_manifest(package)
        rights = manifest.get("rights", {})
        rights_expiry = parse_utc_datetime(rights.get("expires_at"), field="rights.expires_at")
        if rights_expiry is not None and rights_expiry <= reference_time:
            reasons.append("data_rights_expired")
        if final_report and not bool(rights.get("final_report_use_allowed", False)):
            reasons.append("data_rights_block_final_report")
        if self._is_revoked("package", clean, at=reference_time):
            reasons.append("package_revoked")

        signature, envelope, key = self._select_valid_signature(
            clean,
            registry=registry,
            environment=requested,
            at=reference_time,
        )
        signature_fp = signature.signature_fingerprint if signature else ""
        key_id = signature.key_id if signature else ""
        signature_expiry = signature.expires_at if signature else ""
        key_valid_until = str(key.get("valid_until", "")) if key else ""
        parent = signature.parent_package_fingerprint if signature else ""
        if signature is None:
            reasons.append("trusted_detached_signature_missing")
        elif self._is_revoked("signature", signature.signature_fingerprint, at=reference_time):
            reasons.append("signature_revoked")
        if key is None:
            reasons.append("trusted_key_missing")
        elif self._is_revoked("key", str(key.get("key_id", "")), at=reference_time):
            reasons.append("signing_key_revoked")

        latest_reviews = self.list_reviews(clean, latest_only=True)
        review_fps = tuple(item.decision_fingerprint for item in latest_reviews)
        latest_by_role: dict[str, list[ReviewDecisionRecord]] = {role: [] for role in REVIEW_ROLES}
        for item in latest_reviews:
            latest_by_role.setdefault(item.reviewer_role, []).append(item)
        if any(item.decision == "reject" for item in latest_reviews):
            reasons.append("review_rejected")
        for role in self.REQUIRED_REVIEWS[requested]:
            if not any(item.decision == "approve" for item in latest_by_role.get(role, [])):
                reasons.append(f"{role}_approval_missing")

        promotion = self._latest_promotion(clean)
        promotion_id = promotion.promotion_id if promotion else ""
        state_promotion_id = str(environment_state.get("promotion_id", ""))
        if current in {"validation", "production"}:
            if (
                promotion is None
                or promotion.target_environment != current
                or promotion.promotion_id != state_promotion_id
            ):
                reasons.append(f"{current}_promotion_evidence_missing_or_mismatched")
        if requested == "production" and current != "production" and final_report:
            reasons.append("package_not_promoted_to_production")
        if requested == "validation" and current == "development":
            warnings.append("package_not_yet_promoted_to_validation")

        deterministic = {
            "project_id": self.project_id,
            "package_fingerprint": clean,
            "requested_environment": requested,
            "current_environment": current,
            "final_report": bool(final_report),
            "reasons": sorted(set(reasons)),
            "warnings": sorted(set(warnings)),
            "signature_fingerprint": signature_fp,
            "key_id": key_id,
            "registry_fingerprint": registry_fp,
            "review_decision_fingerprints": review_fps,
            "promotion_id": promotion_id,
        }
        decision_id = "trust-" + sha256_hex(canonical_json_bytes(deterministic))[:20]
        return CalibrationPackageTrustDecision(
            schema=CALIBRATION_TRUST_DECISION_SCHEMA,
            generated_at=reference_time.isoformat(timespec="seconds"),
            decision_id=decision_id,
            project_id=self.project_id,
            package_fingerprint=clean,
            requested_environment=requested,
            current_environment=current,
            final_report=bool(final_report),
            passed=not reasons,
            reasons=tuple(dict.fromkeys(reasons)),
            warnings=tuple(dict.fromkeys(warnings)),
            signature_fingerprint=signature_fp,
            key_id=key_id,
            trust_registry_fingerprint=registry_fp,
            review_decision_fingerprints=review_fps,
            promotion_id=promotion_id,
            parent_package_fingerprint=parent,
            rights_expires_at=str(rights.get("expires_at", "")),
            signature_expires_at=signature_expiry,
            key_valid_until=key_valid_until,
        )

    def promote(self, package_fingerprint: str, *, target_environment: str) -> PromotionRecord:
        clean = self._clean_fingerprint(package_fingerprint)
        current = self.current_environment(clean)
        target = str(target_environment).strip()
        if target not in ENVIRONMENTS:
            raise CalibrationPackageTrustError(f"unsupported target environment: {target}")
        expected_index = ENVIRONMENTS.index(current) + 1
        if expected_index >= len(ENVIRONMENTS) or ENVIRONMENTS[expected_index] != target:
            raise CalibrationPackageTrustError(
                f"controlled promotion must follow development -> validation -> production; current={current}, target={target}"
            )
        decision = self.evaluate(clean, requested_environment=target, final_report=False)
        decision.assert_trusted()
        promotion_payload = {
            "schema": CALIBRATION_PROMOTION_RECORD_SCHEMA,
            "project_id": self.project_id,
            "package_fingerprint": clean,
            "source_environment": current,
            "target_environment": target,
            "promoted_at": utc_now_iso(),
            "trust_decision_id": decision.decision_id,
            "signature_fingerprint": decision.signature_fingerprint,
            "key_id": decision.key_id,
            "review_decision_fingerprints": list(decision.review_decision_fingerprints),
            "parent_package_fingerprint": decision.parent_package_fingerprint,
        }
        promotion_payload["promotion_id"] = "prom-" + immutable_record_fingerprint(
            promotion_payload, fingerprint_field="promotion_id"
        )[:20]
        destination = self.promotions_root / clean / f"{promotion_payload['promotion_id']}.json"
        self._write_immutable_json(destination, promotion_payload, label="promotion record")
        state = {
            "schema": self.ENVIRONMENT_STATE_SCHEMA,
            "project_id": self.project_id,
            "package_fingerprint": clean,
            "environment": target,
            "promotion_id": promotion_payload["promotion_id"],
            "updated_at": promotion_payload["promoted_at"],
        }
        self._atomic_write_json(self.environments_root / f"{clean}.json", state)
        return self._promotion_from_dict(promotion_payload)

    def assert_production_authorized(self, package_fingerprint: str, *, final_report: bool = True) -> CalibrationPackageTrustDecision:
        decision = self.evaluate(
            package_fingerprint,
            requested_environment="production",
            final_report=final_report,
        )
        decision.assert_trusted()
        return decision

    def monitor_expiry(self, *, warning_window_days: int = 30, now: datetime | None = None) -> CalibrationPackageExpiryReport:
        if warning_window_days < 0:
            raise ValueError("warning_window_days cannot be negative")
        reference_time = (now or self._utc_now_dt()).astimezone(timezone.utc)
        threshold = reference_time + timedelta(days=warning_window_days)
        items: list[ExpiryMonitorItem] = []
        registry = self.load_registry()
        for key in registry.get("keys", []):
            expires = parse_utc_datetime(key.get("valid_until"), field="key.valid_until")
            if expires is not None:
                items.append(self._expiry_item("key", str(key.get("key_id", "")), "", expires, reference_time, threshold))
        for package in self._package_entries():
            fingerprint = str(package.get("package_fingerprint", ""))
            manifest = self._load_package_manifest(package)
            rights_expiry = parse_utc_datetime(manifest.get("rights", {}).get("expires_at"), field="rights.expires_at")
            if rights_expiry is not None:
                items.append(self._expiry_item("data_rights", fingerprint, fingerprint, rights_expiry, reference_time, threshold))
            for signature in self.list_signatures(fingerprint):
                expires = parse_utc_datetime(signature.expires_at, field="signature.expires_at")
                if expires is not None:
                    items.append(self._expiry_item("signature", signature.signature_fingerprint, fingerprint, expires, reference_time, threshold))
        expired = sum(item.status == "expired" for item in items)
        expiring = sum(item.status == "expiring" for item in items)
        return CalibrationPackageExpiryReport(
            schema=CALIBRATION_EXPIRY_REPORT_SCHEMA,
            generated_at=reference_time.isoformat(timespec="seconds"),
            project_id=self.project_id,
            warning_window_days=warning_window_days,
            passed=expired == 0,
            expired_count=expired,
            expiring_count=expiring,
            items=tuple(sorted(items, key=lambda item: (item.status, item.expires_at, item.item_type, item.item_id))),
        )

    def _select_valid_signature(
        self,
        package_fingerprint: str,
        *,
        registry: Mapping[str, Any],
        environment: str,
        at: datetime,
    ) -> tuple[DetachedSignatureRecord | None, dict[str, Any] | None, Mapping[str, Any] | None]:
        candidates = list(self.list_signatures(package_fingerprint))
        candidates.sort(key=lambda item: (item.signed_at, item.signature_fingerprint), reverse=True)
        for record in candidates:
            key = self._key_record(registry, record.key_id)
            if key is None or not self._key_scope_allows(key, environment=environment, at=at):
                continue
            if self._is_revoked("package", package_fingerprint, at=at):
                continue
            if self._is_revoked("key", record.key_id, at=at):
                continue
            if self._is_revoked("signature", record.signature_fingerprint, at=at):
                continue
            envelope = json.loads((self.project_root / record.storage_path).read_text(encoding="utf-8"))
            expires = parse_utc_datetime(record.expires_at, field="signature.expires_at")
            if expires is not None and expires <= at:
                continue
            if not verify_detached_signature(envelope, public_key=load_public_key_base64(key.get("public_key_base64"))):
                continue
            return record, envelope, key
        return None, None, None

    def _key_scope_allows(self, key: Mapping[str, Any], *, environment: str, at: datetime) -> bool:
        if str(key.get("status", "")) != "active":
            return False
        if SIGNING_PURPOSE not in key.get("purposes", []):
            return False
        projects = {str(item) for item in key.get("allowed_projects", [])}
        if self.project_id not in projects and "*" not in projects:
            return False
        if environment not in {str(item) for item in key.get("allowed_environments", [])}:
            return False
        valid_from = parse_utc_datetime(key.get("valid_from"), field="key.valid_from")
        valid_until = parse_utc_datetime(key.get("valid_until"), field="key.valid_until")
        if valid_from is not None and at < valid_from:
            return False
        if valid_until is not None and at >= valid_until:
            return False
        return True

    def _is_revoked(self, target_type: str, target_id: str, *, at: datetime) -> bool:
        for record in self.list_revocations(target_type=target_type, target_id=target_id):
            effective = parse_utc_datetime(record.effective_at, field="effective_at", required=True)
            if effective is not None and effective <= at:
                return True
        return False

    def _package_entries(self) -> tuple[dict[str, Any], ...]:
        index = self.operator_repository_root / "package_index.json"
        if not index.exists():
            return ()
        try:
            payload = json.loads(index.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ()
        if payload.get("project_id") != self.project_id:
            return ()
        return tuple(item for item in payload.get("packages", []) if isinstance(item, dict))

    def _package_entry(self, package_fingerprint: str) -> dict[str, Any]:
        clean = self._clean_fingerprint(package_fingerprint)
        for item in self._package_entries():
            if str(item.get("package_fingerprint", "")).lower() == clean:
                manifest = self._load_package_manifest(item)
                if operator_package_fingerprint(manifest) != clean:
                    raise CalibrationPackageTrustError("stored operator package manifest was modified")
                return item
        raise KeyError(f"operator calibration package not found: {clean}")

    def _load_package_manifest(self, package: Mapping[str, Any]) -> dict[str, Any]:
        path = self.project_root / str(package.get("storage_path", "")) / PACKAGE_MANIFEST_NAME
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CalibrationPackageTrustError("stored operator package manifest is unavailable") from exc
        if not isinstance(manifest, dict):
            raise CalibrationPackageTrustError("stored operator package manifest root must be an object")
        return manifest

    @staticmethod
    def _key_record(registry: Mapping[str, Any], key_id: str) -> Mapping[str, Any] | None:
        clean = str(key_id).strip()
        return next((item for item in registry.get("keys", []) if str(item.get("key_id", "")) == clean), None)

    def _lineage_would_cycle(self, package_fingerprint: str, parent_fingerprint: str) -> bool:
        target = package_fingerprint
        current = parent_fingerprint
        visited = {target}
        while current:
            if current in visited:
                return True
            visited.add(current)
            signatures = self.list_signatures(current)
            current = signatures[-1].parent_package_fingerprint if signatures else ""
        return False

    def _latest_review_by_reviewer(self, package_fingerprint: str, reviewer_id: str, reviewer_role: str) -> ReviewDecisionRecord | None:
        matches = [
            item
            for item in self.list_reviews(package_fingerprint)
            if item.reviewer_id == reviewer_id and item.reviewer_role == reviewer_role
        ]
        if not matches:
            return None
        referenced = {item.previous_decision_fingerprint for item in matches if item.previous_decision_fingerprint}
        terminal = [item for item in matches if item.decision_fingerprint not in referenced]
        return max(terminal or matches, key=lambda item: (item.decided_at, item.decision_fingerprint))

    def _latest_promotion(self, package_fingerprint: str) -> PromotionRecord | None:
        root = self.promotions_root / self._clean_fingerprint(package_fingerprint)
        records: list[PromotionRecord] = []
        if root.exists():
            for path in sorted(root.glob("*.json")):
                try:
                    records.append(self._promotion_from_dict(json.loads(path.read_text(encoding="utf-8"))))
                except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
                    continue
        return (
            sorted(
                records,
                key=lambda item: (
                    ENVIRONMENTS.index(item.target_environment),
                    item.promoted_at,
                    item.promotion_id,
                ),
            )[-1]
            if records
            else None
        )

    def _signature_path_by_id(self, signature_fingerprint: str) -> Path | None:
        matches = list(self.signatures_root.glob(f"*/{self._clean_fingerprint(signature_fingerprint)}.json"))
        return matches[0] if matches else None

    @staticmethod
    def _review_from_dict(payload: Mapping[str, Any]) -> ReviewDecisionRecord:
        expected = immutable_record_fingerprint(payload, fingerprint_field="decision_fingerprint")
        if str(payload.get("decision_fingerprint", "")) != expected:
            raise ValueError("review decision fingerprint mismatch")
        return ReviewDecisionRecord(
            schema=str(payload["schema"]),
            project_id=str(payload["project_id"]),
            package_fingerprint=str(payload["package_fingerprint"]),
            reviewer_id=str(payload["reviewer_id"]),
            reviewer_name=str(payload["reviewer_name"]),
            reviewer_role=str(payload["reviewer_role"]),
            decision=str(payload["decision"]),
            comment=str(payload["comment"]),
            decided_at=str(payload["decided_at"]),
            previous_decision_fingerprint=str(payload.get("previous_decision_fingerprint", "")),
            decision_fingerprint=str(payload["decision_fingerprint"]),
        )

    @staticmethod
    def _revocation_from_dict(payload: Mapping[str, Any]) -> RevocationRecord:
        expected = immutable_record_fingerprint(payload, fingerprint_field="revocation_fingerprint")
        if str(payload.get("revocation_fingerprint", "")) != expected:
            raise ValueError("revocation fingerprint mismatch")
        return RevocationRecord(
            schema=str(payload["schema"]),
            project_id=str(payload["project_id"]),
            target_type=str(payload["target_type"]),
            target_id=str(payload["target_id"]),
            revoked_by=str(payload["revoked_by"]),
            reviewer_role=str(payload["reviewer_role"]),
            reason=str(payload["reason"]),
            effective_at=str(payload["effective_at"]),
            recorded_at=str(payload["recorded_at"]),
            revocation_fingerprint=str(payload["revocation_fingerprint"]),
        )

    @staticmethod
    def _promotion_from_dict(payload: Mapping[str, Any]) -> PromotionRecord:
        deterministic = dict(payload)
        promotion_id = str(deterministic.pop("promotion_id", ""))
        expected = "prom-" + sha256_hex(canonical_json_bytes(deterministic))[:20]
        if promotion_id != expected:
            raise ValueError("promotion fingerprint mismatch")
        return PromotionRecord(
            schema=str(payload["schema"]),
            project_id=str(payload["project_id"]),
            package_fingerprint=str(payload["package_fingerprint"]),
            source_environment=str(payload["source_environment"]),
            target_environment=str(payload["target_environment"]),
            promoted_at=str(payload["promoted_at"]),
            trust_decision_id=str(payload["trust_decision_id"]),
            signature_fingerprint=str(payload["signature_fingerprint"]),
            key_id=str(payload["key_id"]),
            review_decision_fingerprints=tuple(str(item) for item in payload.get("review_decision_fingerprints", ())),
            parent_package_fingerprint=str(payload.get("parent_package_fingerprint", "")),
            promotion_id=promotion_id,
        )

    @staticmethod
    def _expiry_item(item_type: str, item_id: str, package_fingerprint: str, expires_at: datetime, now: datetime, threshold: datetime) -> ExpiryMonitorItem:
        remaining = int((expires_at - now).total_seconds() // 86400)
        status = "expired" if expires_at <= now else ("expiring" if expires_at <= threshold else "valid")
        return ExpiryMonitorItem(
            item_type=item_type,
            item_id=item_id,
            package_fingerprint=package_fingerprint,
            expires_at=expires_at.isoformat(timespec="seconds"),
            status=status,
            days_remaining=remaining,
        )

    @staticmethod
    def _clean_fingerprint(value: object) -> str:
        text = str(value or "").strip().lower()
        if len(text) < 16 or any(char not in "0123456789abcdef-" for char in text):
            raise CalibrationPackageTrustError(f"invalid fingerprint: {text!r}")
        return text

    @staticmethod
    def _read_json_source(source: bytes | bytearray | Path | str, *, label: str) -> dict[str, Any]:
        try:
            if isinstance(source, (bytes, bytearray)):
                raw = bytes(source)
            else:
                raw = Path(source).read_bytes()
            payload = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CalibrationPackageTrustError(f"{label} is not valid UTF-8 JSON") from exc
        if not isinstance(payload, dict):
            raise CalibrationPackageTrustError(f"{label} root must be an object")
        return payload

    @staticmethod
    def _write_immutable_json(path: Path, payload: Mapping[str, Any], *, label: str) -> None:
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise CalibrationPackageTrustError(f"stored {label} is unreadable") from exc
            if existing != dict(payload):
                raise CalibrationPackageTrustError(f"stored {label} fingerprint collision")
            return
        CalibrationPackageTrustApplicationService._atomic_write_json(path, payload)

    @staticmethod
    def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)

    @staticmethod
    def _utc_now_dt() -> datetime:
        return datetime.now(timezone.utc)
