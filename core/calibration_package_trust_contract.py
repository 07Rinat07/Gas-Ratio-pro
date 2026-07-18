"""Stage 5.3 trust contracts for operator calibration packages.

The operator calibration ZIP remains immutable. Trust evidence is detached and
contains only public-key signatures, review decisions, revocations, lineage and
environment-promotion records. Private signing keys are never stored by the
application or included in a release archive.
"""
from __future__ import annotations

from base64 import b64decode, b64encode
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

CALIBRATION_TRUST_REGISTRY_SCHEMA = "gas-ratio-pro/calibration-trust-registry/v1"
CALIBRATION_DETACHED_SIGNATURE_SCHEMA = "gas-ratio-pro/calibration-detached-signature/v1"
CALIBRATION_REVIEW_DECISION_SCHEMA = "gas-ratio-pro/calibration-review-decision/v1"
CALIBRATION_REVOCATION_SCHEMA = "gas-ratio-pro/calibration-revocation/v1"
CALIBRATION_PROMOTION_RECORD_SCHEMA = "gas-ratio-pro/calibration-promotion-record/v1"
CALIBRATION_TRUST_DECISION_SCHEMA = "gas-ratio-pro/calibration-trust-decision/v1"
CALIBRATION_EXPIRY_REPORT_SCHEMA = "gas-ratio-pro/calibration-expiry-report/v1"

SIGNATURE_ALGORITHM = "Ed25519"
SIGNING_PURPOSE = "operator_calibration_package_signing"
ENVIRONMENTS = ("development", "validation", "production")
REVIEW_ROLES = ("technical_reviewer", "data_governance_reviewer")
REVIEW_DECISIONS = ("approve", "reject")
REVOCATION_TARGETS = ("package", "key", "signature")


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_hex(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def parse_utc_datetime(value: object, *, field: str, required: bool = False) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        if required:
            raise ValueError(f"{field} is required")
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid {field}: {text}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def trust_registry_fingerprint(registry: Mapping[str, Any]) -> str:
    deterministic = dict(registry)
    deterministic.pop("registry_fingerprint", None)
    return sha256_hex(canonical_json_bytes(deterministic))


def detached_signature_payload(envelope: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(envelope)
    payload.pop("signature_base64", None)
    payload.pop("signature_fingerprint", None)
    return payload


def detached_signature_fingerprint(envelope: Mapping[str, Any]) -> str:
    deterministic = dict(envelope)
    deterministic.pop("signature_fingerprint", None)
    return sha256_hex(canonical_json_bytes(deterministic))


def public_key_base64(public_key: Ed25519PublicKey) -> str:
    raw = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return b64encode(raw).decode("ascii")


def load_public_key_base64(value: object) -> Ed25519PublicKey:
    try:
        raw = b64decode(str(value or ""), validate=True)
    except Exception as exc:  # binascii.Error varies between Python versions.
        raise ValueError("public_key_base64 is not valid Base64") from exc
    if len(raw) != 32:
        raise ValueError("Ed25519 public key must contain 32 bytes")
    return Ed25519PublicKey.from_public_bytes(raw)


def validate_trust_registry(registry: Mapping[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    if registry.get("schema") != CALIBRATION_TRUST_REGISTRY_SCHEMA:
        errors.append("unsupported calibration trust registry schema")
    registry_id = str(registry.get("registry_id", "")).strip()
    if not registry_id:
        errors.append("registry_id is required")
    keys = registry.get("keys")
    if not isinstance(keys, list):
        errors.append("keys must be a list")
        keys = []
    seen: set[str] = set()
    for index, item in enumerate(keys):
        if not isinstance(item, Mapping):
            errors.append(f"keys[{index}] must be an object")
            continue
        key_id = str(item.get("key_id", "")).strip()
        if not key_id:
            errors.append(f"keys[{index}].key_id is required")
        elif key_id in seen:
            errors.append(f"duplicate key_id: {key_id}")
        seen.add(key_id)
        if item.get("algorithm") != SIGNATURE_ALGORITHM:
            errors.append(f"keys[{index}].algorithm must be {SIGNATURE_ALGORITHM}")
        try:
            load_public_key_base64(item.get("public_key_base64"))
        except ValueError as exc:
            errors.append(f"keys[{index}]: {exc}")
        if str(item.get("status", "")).strip() not in {"active", "suspended", "revoked"}:
            errors.append(f"keys[{index}].status is invalid")
        purposes = item.get("purposes")
        if not isinstance(purposes, list) or SIGNING_PURPOSE not in purposes:
            errors.append(f"keys[{index}].purposes must include {SIGNING_PURPOSE}")
        projects = item.get("allowed_projects")
        if not isinstance(projects, list) or not projects:
            errors.append(f"keys[{index}].allowed_projects must be a non-empty list")
        environments = item.get("allowed_environments")
        if not isinstance(environments, list) or not environments:
            errors.append(f"keys[{index}].allowed_environments must be a non-empty list")
        elif any(str(value) not in ENVIRONMENTS for value in environments):
            errors.append(f"keys[{index}].allowed_environments contains an unsupported value")
        try:
            valid_from = parse_utc_datetime(item.get("valid_from"), field=f"keys[{index}].valid_from")
            valid_until = parse_utc_datetime(item.get("valid_until"), field=f"keys[{index}].valid_until")
            if valid_from and valid_until and valid_until <= valid_from:
                errors.append(f"keys[{index}].valid_until must be after valid_from")
        except ValueError as exc:
            errors.append(str(exc))
    declared = str(registry.get("registry_fingerprint", "")).strip().lower()
    expected = trust_registry_fingerprint(registry)
    if declared != expected:
        errors.append("registry_fingerprint does not match canonical registry content")
    return tuple(errors)


def build_trust_registry(
    *,
    registry_id: str,
    keys: Sequence[Mapping[str, Any]],
    revision: int = 1,
    generated_at: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema": CALIBRATION_TRUST_REGISTRY_SCHEMA,
        "registry_id": str(registry_id),
        "revision": int(revision),
        "generated_at": generated_at or utc_now_iso(),
        "keys": [dict(item) for item in keys],
    }
    payload["registry_fingerprint"] = trust_registry_fingerprint(payload)
    errors = validate_trust_registry(payload)
    if errors:
        raise ValueError("; ".join(errors))
    return payload


def build_trust_key_record(
    *,
    key_id: str,
    public_key: Ed25519PublicKey,
    owner: str,
    organization_id: str,
    allowed_projects: Sequence[str],
    allowed_environments: Sequence[str] = ("validation", "production"),
    status: str = "active",
    valid_from: str | None = None,
    valid_until: str | None = None,
) -> dict[str, Any]:
    return {
        "key_id": str(key_id),
        "algorithm": SIGNATURE_ALGORITHM,
        "public_key_base64": public_key_base64(public_key),
        "owner": str(owner),
        "organization_id": str(organization_id),
        "status": str(status),
        "purposes": [SIGNING_PURPOSE],
        "allowed_projects": [str(item) for item in allowed_projects],
        "allowed_environments": [str(item) for item in allowed_environments],
        "valid_from": valid_from or "",
        "valid_until": valid_until or "",
    }


def build_detached_signature(
    *,
    private_key: Ed25519PrivateKey,
    package_fingerprint: str,
    key_id: str,
    project_id: str,
    signer_id: str,
    signer_name: str,
    organization_id: str,
    signed_at: str | None = None,
    expires_at: str | None = None,
    parent_package_fingerprint: str = "",
    lineage_relation: str = "root",
    lineage_reason: str = "",
) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "schema": CALIBRATION_DETACHED_SIGNATURE_SCHEMA,
        "algorithm": SIGNATURE_ALGORITHM,
        "package_fingerprint": str(package_fingerprint).lower(),
        "key_id": str(key_id),
        "project_id": str(project_id),
        "signer": {
            "signer_id": str(signer_id),
            "name": str(signer_name),
            "organization_id": str(organization_id),
        },
        "signed_at": signed_at or utc_now_iso(),
        "expires_at": expires_at or "",
        "lineage": {
            "parent_package_fingerprint": str(parent_package_fingerprint).lower(),
            "relation": str(lineage_relation),
            "reason": str(lineage_reason),
        },
    }
    signature = private_key.sign(canonical_json_bytes(detached_signature_payload(envelope)))
    envelope["signature_base64"] = b64encode(signature).decode("ascii")
    envelope["signature_fingerprint"] = detached_signature_fingerprint(envelope)
    return envelope


def validate_detached_signature_structure(envelope: Mapping[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    if envelope.get("schema") != CALIBRATION_DETACHED_SIGNATURE_SCHEMA:
        errors.append("unsupported detached-signature schema")
    if envelope.get("algorithm") != SIGNATURE_ALGORITHM:
        errors.append(f"signature algorithm must be {SIGNATURE_ALGORITHM}")
    for field in ("package_fingerprint", "key_id", "project_id"):
        if not str(envelope.get(field, "")).strip():
            errors.append(f"{field} is required")
    signer = envelope.get("signer")
    if not isinstance(signer, Mapping):
        errors.append("signer must be an object")
    else:
        for field in ("signer_id", "name", "organization_id"):
            if not str(signer.get(field, "")).strip():
                errors.append(f"signer.{field} is required")
    try:
        parse_utc_datetime(envelope.get("signed_at"), field="signed_at", required=True)
        expires = parse_utc_datetime(envelope.get("expires_at"), field="expires_at")
        signed = parse_utc_datetime(envelope.get("signed_at"), field="signed_at", required=True)
        if signed and expires and expires <= signed:
            errors.append("expires_at must be after signed_at")
    except ValueError as exc:
        errors.append(str(exc))
    lineage = envelope.get("lineage")
    if not isinstance(lineage, Mapping):
        errors.append("lineage must be an object")
    else:
        relation = str(lineage.get("relation", "")).strip()
        parent = str(lineage.get("parent_package_fingerprint", "")).strip()
        if relation not in {"root", "supersedes", "derived_from", "recalibrated_from"}:
            errors.append("lineage.relation is invalid")
        if relation == "root" and parent:
            errors.append("root lineage cannot declare a parent package")
        if relation != "root" and not parent:
            errors.append("non-root lineage requires parent_package_fingerprint")
        if parent and parent == str(envelope.get("package_fingerprint", "")).strip():
            errors.append("lineage parent cannot be the package itself")
    try:
        signature = b64decode(str(envelope.get("signature_base64", "")), validate=True)
        if len(signature) != 64:
            errors.append("Ed25519 signature must contain 64 bytes")
    except Exception:
        errors.append("signature_base64 is invalid")
    declared = str(envelope.get("signature_fingerprint", "")).strip().lower()
    if declared != detached_signature_fingerprint(envelope):
        errors.append("signature_fingerprint does not match detached signature content")
    return tuple(errors)


def verify_detached_signature(
    envelope: Mapping[str, Any],
    *,
    public_key: Ed25519PublicKey,
) -> bool:
    try:
        signature = b64decode(str(envelope.get("signature_base64", "")), validate=True)
        public_key.verify(signature, canonical_json_bytes(detached_signature_payload(envelope)))
    except (InvalidSignature, ValueError, TypeError):
        return False
    return True


def immutable_record_fingerprint(payload: Mapping[str, Any], *, fingerprint_field: str) -> str:
    deterministic = dict(payload)
    deterministic.pop(fingerprint_field, None)
    return sha256_hex(canonical_json_bytes(deterministic))
