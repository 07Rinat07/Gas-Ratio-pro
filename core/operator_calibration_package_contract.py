"""Stage 5.2 contracts for operator-owned calibration packages.

The package format is intentionally small and deterministic.  A package is a
ZIP archive with exactly three files at its root::

    manifest.json
    calibration_registry.json
    calibration_dataset.json

The manifest carries data-rights declarations and SHA-256 checksums for the two
calibration payloads.  ``package_fingerprint`` is the SHA-256 hash of the
canonical manifest with that field removed.  This makes every imported source
immutable and allows project-scoped authorization evidence to reference one
exact operator dataset version.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from typing import Any, Mapping

OPERATOR_CALIBRATION_PACKAGE_SCHEMA = "gas-ratio-pro/operator-calibration-package/v1"
OPERATOR_CALIBRATION_IMPORT_RECORD_SCHEMA = "gas-ratio-pro/operator-calibration-import-record/v1"
OPERATOR_CALIBRATION_COMPARISON_SCHEMA = "gas-ratio-pro/operator-calibration-comparison/v1"
PROJECT_AUTHORIZATION_PACKAGE_SCHEMA = "gas-ratio-pro/project-petrophysical-authorization-package/v1"

PACKAGE_MANIFEST_NAME = "manifest.json"
PACKAGE_REGISTRY_NAME = "calibration_registry.json"
PACKAGE_DATASET_NAME = "calibration_dataset.json"
PACKAGE_FILE_NAMES = (PACKAGE_MANIFEST_NAME, PACKAGE_REGISTRY_NAME, PACKAGE_DATASET_NAME)

_ALLOWED_LEGAL_STATUS = {"operator_owned", "licensed", "public_domain"}
_ALLOWED_CLASSIFICATION = {"public", "internal", "confidential", "restricted"}
_SAFE_COMPONENT = re.compile(r"^[0-9A-Za-z._-]{1,96}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_hex(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def safe_package_component(value: object, *, field: str) -> str:
    text = str(value or "").strip()
    if not _SAFE_COMPONENT.fullmatch(text) or text in {".", ".."} or ".." in text:
        raise ValueError(f"Invalid operator calibration {field}: {text!r}")
    return text


def rights_fingerprint(rights: Mapping[str, Any]) -> str:
    return sha256_hex(canonical_json_bytes(rights))


def operator_package_fingerprint(manifest: Mapping[str, Any]) -> str:
    deterministic = dict(manifest)
    deterministic.pop("package_fingerprint", None)
    return sha256_hex(canonical_json_bytes(deterministic))


def _parse_iso_datetime(value: object, *, field: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Invalid {field}: {text}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def validate_operator_package_manifest(
    manifest: Mapping[str, Any],
    *,
    project_id: str,
    expected_method_registry_fingerprint: str,
    now: datetime | None = None,
) -> tuple[str, ...]:
    """Validate schema, project scope, rights and immutable fingerprints."""

    errors: list[str] = []
    if manifest.get("schema") != OPERATOR_CALIBRATION_PACKAGE_SCHEMA:
        errors.append(f"unsupported operator package schema: {manifest.get('schema')}")

    try:
        safe_package_component(manifest.get("package_id"), field="package_id")
    except ValueError as exc:
        errors.append(str(exc))
    try:
        safe_package_component(manifest.get("version"), field="version")
    except ValueError as exc:
        errors.append(str(exc))

    operator = manifest.get("operator")
    if not isinstance(operator, Mapping):
        errors.append("operator metadata must be an object")
    else:
        if not str(operator.get("name", "")).strip():
            errors.append("operator.name is required")
        if not str(operator.get("organization_id", "")).strip():
            errors.append("operator.organization_id is required")

    scope = manifest.get("project_scope")
    if not isinstance(scope, list) or not scope:
        errors.append("project_scope must be a non-empty list")
    else:
        normalized_scope = {str(item).strip() for item in scope if str(item).strip()}
        if project_id not in normalized_scope and "*" not in normalized_scope:
            errors.append(f"package is not scoped to project: {project_id}")

    rights = manifest.get("rights")
    if not isinstance(rights, Mapping):
        errors.append("rights metadata must be an object")
    else:
        legal_status = str(rights.get("legal_status", "")).strip()
        if legal_status not in _ALLOWED_LEGAL_STATUS:
            errors.append(f"unsupported rights.legal_status: {legal_status}")
        if not str(rights.get("owner", "")).strip():
            errors.append("rights.owner is required")
        if not str(rights.get("legal_basis", "")).strip():
            errors.append("rights.legal_basis is required")
        if str(rights.get("data_classification", "")).strip() not in _ALLOWED_CLASSIFICATION:
            errors.append("rights.data_classification is invalid")
        for flag in ("processing_allowed", "derivative_analysis_allowed"):
            if rights.get(flag) is not True:
                errors.append(f"rights.{flag} must be true")
        if not isinstance(rights.get("final_report_use_allowed"), bool):
            errors.append("rights.final_report_use_allowed must be boolean")
        if not isinstance(rights.get("redistribution_allowed"), bool):
            errors.append("rights.redistribution_allowed must be boolean")
        try:
            expiry = _parse_iso_datetime(rights.get("expires_at"), field="rights.expires_at")
            reference_time = now or datetime.now(timezone.utc)
            if expiry is not None and expiry <= reference_time.astimezone(timezone.utc):
                errors.append("operator package rights have expired")
        except ValueError as exc:
            errors.append(str(exc))

    calculation_contract = manifest.get("calculation_contract")
    if not isinstance(calculation_contract, Mapping):
        errors.append("calculation_contract must be an object")
    else:
        actual = str(calculation_contract.get("method_registry_fingerprint", "")).strip()
        if actual != expected_method_registry_fingerprint:
            errors.append("method registry fingerprint does not match the active production contract")
        if calculation_contract.get("formula_changes") is not False:
            errors.append("operator calibration packages cannot declare formula changes")

    files = manifest.get("files")
    if not isinstance(files, Mapping):
        errors.append("files must be an object")
    else:
        expected = {PACKAGE_REGISTRY_NAME, PACKAGE_DATASET_NAME}
        if set(files) != expected:
            errors.append("files must contain calibration_registry.json and calibration_dataset.json only")
        for name in expected:
            record = files.get(name)
            if not isinstance(record, Mapping):
                errors.append(f"files.{name} must be an object")
                continue
            digest = str(record.get("sha256", "")).strip().lower()
            if not _SHA256.fullmatch(digest):
                errors.append(f"files.{name}.sha256 must be a lowercase SHA-256 value")
            try:
                size = int(record.get("size_bytes", -1))
                if size <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(f"files.{name}.size_bytes must be positive")

    declared = str(manifest.get("package_fingerprint", "")).strip().lower()
    expected_fingerprint = operator_package_fingerprint(manifest)
    if not _SHA256.fullmatch(declared):
        errors.append("package_fingerprint must be a lowercase SHA-256 value")
    elif declared != expected_fingerprint:
        errors.append("package_fingerprint does not match canonical manifest content")

    try:
        _parse_iso_datetime(manifest.get("created_at"), field="created_at")
    except ValueError as exc:
        errors.append(str(exc))
    return tuple(errors)


def build_operator_package_manifest(
    *,
    package_id: str,
    version: str,
    created_at: str,
    operator: Mapping[str, Any],
    project_scope: list[str] | tuple[str, ...],
    rights: Mapping[str, Any],
    method_registry_fingerprint: str,
    registry_bytes: bytes,
    dataset_bytes: bytes,
    notes: str = "",
) -> dict[str, Any]:
    """Build a canonical manifest for tests, tooling and documented examples."""

    manifest: dict[str, Any] = {
        "schema": OPERATOR_CALIBRATION_PACKAGE_SCHEMA,
        "package_id": safe_package_component(package_id, field="package_id"),
        "version": safe_package_component(version, field="version"),
        "created_at": str(created_at),
        "operator": dict(operator),
        "project_scope": [str(item) for item in project_scope],
        "rights": dict(rights),
        "calculation_contract": {
            "method_registry_fingerprint": str(method_registry_fingerprint),
            "formula_changes": False,
        },
        "files": {
            PACKAGE_REGISTRY_NAME: {
                "sha256": sha256_hex(registry_bytes),
                "size_bytes": len(registry_bytes),
            },
            PACKAGE_DATASET_NAME: {
                "sha256": sha256_hex(dataset_bytes),
                "size_bytes": len(dataset_bytes),
            },
        },
        "notes": str(notes),
    }
    manifest["package_fingerprint"] = operator_package_fingerprint(manifest)
    return manifest
