"""Project-scoped Stage 5.2 operator calibration package boundary.

This service owns package import, immutable storage, version comparison and
project-scoped report authorization.  It never changes petrophysical formulas;
all numerical work is delegated to the production method executor through the
existing validation and calibration services.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import tempfile
from typing import Any, Mapping, Sequence
from zipfile import BadZipFile, ZipFile

from core.operator_calibration_package_contract import (
    OPERATOR_CALIBRATION_COMPARISON_SCHEMA,
    OPERATOR_CALIBRATION_IMPORT_RECORD_SCHEMA,
    PACKAGE_DATASET_NAME,
    PACKAGE_FILE_NAMES,
    PACKAGE_MANIFEST_NAME,
    PACKAGE_REGISTRY_NAME,
    PROJECT_AUTHORIZATION_PACKAGE_SCHEMA,
    canonical_json_bytes,
    operator_package_fingerprint,
    rights_fingerprint,
    safe_package_component,
    sha256_hex,
    validate_operator_package_manifest,
)
from core.petrophysical_calibration_contract import (
    FIELD_CALIBRATION_DATASET_SCHEMA,
    FIELD_CALIBRATION_REGISTRY_SCHEMA,
    validate_field_calibration_contract,
)
from core.storage_lifecycle import DeleteEngine
from core.petrophysical_validation_contract import (
    contract_fingerprint,
    load_petrophysical_method_registry,
)
from projects.repository import safe_project_id
from services.petrophysical_calibration_application_service import (
    MethodCalibrationResult,
    PetrophysicalCalibrationApplicationService,
    PetrophysicalCalibrationReport,
)
from services.petrophysical_report_authorization_application_service import (
    PetrophysicalReportAuthorizationApplicationService,
)
from services.petrophysical_validation_application_service import (
    PetrophysicalValidationApplicationService,
)


class OperatorCalibrationPackageError(ValueError):
    """Raised when an operator package violates the Stage 5.2 contract."""


class OperatorCalibrationVersionConflict(OperatorCalibrationPackageError):
    """Raised when one package id/version is reused with different content."""


@dataclass(frozen=True, slots=True)
class OperatorCalibrationPackageRecord:
    schema: str
    project_id: str
    package_id: str
    version: str
    package_fingerprint: str
    rights_fingerprint: str
    imported_at: str
    operator_name: str
    legal_status: str
    data_classification: str
    final_report_use_allowed: bool
    redistribution_allowed: bool
    method_ids: tuple[str, ...]
    calibration_gate_id: str
    calibration_contract_fingerprint: str
    storage_path: str
    active: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["method_ids"] = list(self.method_ids)
        return payload


@dataclass(frozen=True, slots=True)
class MethodCalibrationAggregate:
    method_id: str
    case_count: int
    output_count: int
    passed: bool
    final_report_calibrated: bool
    calibration_policy: str
    rmse: float
    mae: float
    max_abs_error: float
    bias: float
    max_uncertainty_width: float
    mean_uncertainty_width: float


@dataclass(frozen=True, slots=True)
class CalibrationComparisonMethod:
    method_id: str
    status: str
    reference_source: str
    target_source: str
    reference_passed: bool | None
    target_passed: bool | None
    reference_rmse: float | None
    target_rmse: float | None
    rmse_delta: float | None
    reference_max_abs_error: float | None
    target_max_abs_error: float | None
    max_abs_error_delta: float | None
    reference_uncertainty_width: float | None
    target_uncertainty_width: float | None
    uncertainty_width_delta: float | None


@dataclass(frozen=True, slots=True)
class OperatorCalibrationComparisonReport:
    schema: str
    generated_at: str
    comparison_id: str
    project_id: str
    reference_kind: str
    reference_fingerprint: str
    target_fingerprint: str
    reference_gate_id: str
    target_gate_id: str
    passed: bool
    methods: tuple[CalibrationComparisonMethod, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["methods"] = [asdict(item) for item in self.methods]
        return payload


@dataclass(frozen=True, slots=True)
class ProjectMethodAuthorization:
    method_id: str
    calibration_source: str
    numerical_validation_passed: bool
    calibration_passed: bool
    report_policy: str
    rights_allowed: bool
    authorized: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProjectPetrophysicalAuthorizationPackage:
    schema: str
    generated_at: str
    authorization_id: str
    authorization_package_id: str
    project_id: str
    final_report: bool
    passed: bool
    method_ids: tuple[str, ...]
    validation_gate_id: str
    calibration_gate_id: str
    baseline_calibration_gate_id: str
    comparison_id: str
    operator_package_id: str
    operator_package_version: str
    operator_package_fingerprint: str
    rights_fingerprint: str
    validation_contract_fingerprint: str
    calibration_contract_fingerprint: str
    methods: tuple[ProjectMethodAuthorization, ...]
    warnings: tuple[str, ...] = ()

    @property
    def authorization_gate_ids(self) -> tuple[str, ...]:
        return tuple(
            item
            for item in (
                self.validation_gate_id,
                self.baseline_calibration_gate_id,
                self.calibration_gate_id,
                self.comparison_id,
                self.authorization_package_id,
            )
            if item
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["method_ids"] = list(self.method_ids)
        payload["methods"] = [
            {**asdict(item), "reasons": list(item.reasons)} for item in self.methods
        ]
        payload["warnings"] = list(self.warnings)
        payload["authorization_gate_ids"] = list(self.authorization_gate_ids)
        return payload

    def assert_authorized(self) -> None:
        if not self.passed:
            blocked = [item.method_id for item in self.methods if not item.authorized]
            raise PermissionError(
                "Project-scoped petrophysical report authorization failed: "
                + ", ".join(blocked)
            )


class OperatorCalibrationPackageApplicationService:
    """Import and use immutable operator calibration packages for one project."""

    MAX_PACKAGE_BYTES = 32 * 1024 * 1024
    MAX_MEMBER_BYTES = 16 * 1024 * 1024
    INDEX_SCHEMA = "gas-ratio-pro/operator-calibration-package-index/v1"
    ACTIVE_SCHEMA = "gas-ratio-pro/operator-calibration-active-selection/v1"

    def __init__(
        self,
        *,
        projects_root: Path | str,
        application_root: Path | str,
        project_id: str,
        validation_service: PetrophysicalValidationApplicationService | None = None,
        baseline_calibration_service: PetrophysicalCalibrationApplicationService | None = None,
        baseline_authorization_service: PetrophysicalReportAuthorizationApplicationService | None = None,
        delete_engine: DeleteEngine | None = None,
    ) -> None:
        self.projects_root = Path(projects_root).resolve()
        self.application_root = Path(application_root).resolve()
        self.project_id = safe_project_id(str(project_id))
        self.delete_engine = delete_engine or DeleteEngine(attempts=2, delay_seconds=0.0)
        self.validation_service = validation_service or PetrophysicalValidationApplicationService(
            root=self.application_root
        )
        self.baseline_calibration_service = baseline_calibration_service or PetrophysicalCalibrationApplicationService(
            root=self.application_root,
            validation_service=self.validation_service,
        )
        self.baseline_authorization_service = baseline_authorization_service or PetrophysicalReportAuthorizationApplicationService(
            root=self.application_root,
            validation_service=self.validation_service,
            calibration_service=self.baseline_calibration_service,
        )

    @property
    def project_root(self) -> Path:
        return self.projects_root / self.project_id

    @property
    def repository_root(self) -> Path:
        return self.project_root / "petrophysics" / "operator_calibration"

    @property
    def packages_root(self) -> Path:
        return self.repository_root / "packages"

    @property
    def comparisons_root(self) -> Path:
        return self.repository_root / "comparisons"

    @property
    def authorizations_root(self) -> Path:
        return self.repository_root / "authorizations"

    @property
    def index_path(self) -> Path:
        return self.repository_root / "package_index.json"

    @property
    def active_path(self) -> Path:
        return self.repository_root / "active_package.json"

    def import_package(self, source: bytes | bytearray | Path | str) -> OperatorCalibrationPackageRecord:
        package_bytes = self._read_source(source)
        manifest, registry, dataset, raw_files = self._decode_package(package_bytes)
        method_registry = load_petrophysical_method_registry(
            self.application_root / "config" / "petrophysical_method_registry_v225_9.json"
        )
        method_registry_fingerprint = contract_fingerprint(method_registry)
        manifest_errors = validate_operator_package_manifest(
            manifest,
            project_id=self.project_id,
            expected_method_registry_fingerprint=method_registry_fingerprint,
        )
        if manifest_errors:
            raise OperatorCalibrationPackageError("; ".join(manifest_errors))
        if registry.get("schema") != FIELD_CALIBRATION_REGISTRY_SCHEMA:
            raise OperatorCalibrationPackageError("unsupported calibration registry schema")
        if dataset.get("schema") != FIELD_CALIBRATION_DATASET_SCHEMA:
            raise OperatorCalibrationPackageError("unsupported calibration dataset schema")

        known_ids = {str(item["method_id"]) for item in method_registry.get("methods", [])}
        contract_errors = validate_field_calibration_contract(
            registry,
            dataset,
            known_method_ids=known_ids,
            require_redistribution_allowed=False,
        )
        rights = manifest["rights"]
        expected_owner = str(rights["owner"]).strip()
        expected_legal = str(rights["legal_status"]).strip()
        for calibration_set in dataset.get("calibration_sets", []):
            if str(calibration_set.get("owner", "")).strip() != expected_owner:
                contract_errors += (
                    f"calibration set {calibration_set.get('calibration_id')} owner does not match package rights",
                )
            if str(calibration_set.get("legal_status", "")).strip() != expected_legal:
                contract_errors += (
                    f"calibration set {calibration_set.get('calibration_id')} legal status does not match package rights",
                )
        if contract_errors:
            raise OperatorCalibrationPackageError("; ".join(contract_errors))

        fingerprint = str(manifest["package_fingerprint"])
        package_id = safe_package_component(manifest["package_id"], field="package_id")
        version = safe_package_component(manifest["version"], field="version")
        version_root = self.packages_root / package_id / version
        existing = [item for item in version_root.iterdir()] if version_root.exists() else []
        conflicting = [item.name for item in existing if item.is_dir() and item.name != fingerprint]
        if conflicting:
            raise OperatorCalibrationVersionConflict(
                f"package {package_id} version {version} already exists with another fingerprint"
            )
        destination = version_root / fingerprint
        if destination.exists():
            record = self._load_record(destination / "import_record.json")
            self._update_index(record)
            return self.get_package(record.package_fingerprint)

        with tempfile.TemporaryDirectory(prefix="grp-operator-cal-") as temp_dir:
            temporary_root = Path(temp_dir)
            registry_path = temporary_root / PACKAGE_REGISTRY_NAME
            dataset_path = temporary_root / PACKAGE_DATASET_NAME
            registry_path.write_bytes(raw_files[PACKAGE_REGISTRY_NAME])
            dataset_path.write_bytes(raw_files[PACKAGE_DATASET_NAME])
            calibration_service = PetrophysicalCalibrationApplicationService(
                root=self.application_root,
                registry_path=registry_path,
                dataset_path=dataset_path,
                validation_service=self.validation_service,
                require_redistribution_allowed=False,
            )
            calibration_report = calibration_service.run_gate()
            calibration_report.assert_passed()

            imported_at = self._utc_now()
            record = OperatorCalibrationPackageRecord(
                schema=OPERATOR_CALIBRATION_IMPORT_RECORD_SCHEMA,
                project_id=self.project_id,
                package_id=package_id,
                version=version,
                package_fingerprint=fingerprint,
                rights_fingerprint=rights_fingerprint(rights),
                imported_at=imported_at,
                operator_name=str(manifest["operator"]["name"]),
                legal_status=str(rights["legal_status"]),
                data_classification=str(rights["data_classification"]),
                final_report_use_allowed=bool(rights["final_report_use_allowed"]),
                redistribution_allowed=bool(rights["redistribution_allowed"]),
                method_ids=tuple(sorted({str(item["method_id"]) for item in registry["methods"]})),
                calibration_gate_id=calibration_report.gate_id,
                calibration_contract_fingerprint=calibration_report.contract_fingerprint,
                storage_path=destination.relative_to(self.project_root).as_posix(),
                active=False,
            )

            staging = destination.with_name(destination.name + ".staging")
            if staging.exists():
                self.delete_engine.delete_path(staging, missing_ok=True)
            staging.mkdir(parents=True, exist_ok=False)
            try:
                (staging / "source_package.zip").write_bytes(package_bytes)
                (staging / PACKAGE_MANIFEST_NAME).write_bytes(raw_files[PACKAGE_MANIFEST_NAME])
                (staging / PACKAGE_REGISTRY_NAME).write_bytes(raw_files[PACKAGE_REGISTRY_NAME])
                (staging / PACKAGE_DATASET_NAME).write_bytes(raw_files[PACKAGE_DATASET_NAME])
                self._atomic_write_json(staging / "calibration_evidence.json", calibration_report.to_dict())
                self._atomic_write_json(staging / "import_record.json", record.to_dict())
                destination.parent.mkdir(parents=True, exist_ok=True)
                staging.replace(destination)
            except BaseException:
                try:
                    self.delete_engine.delete_path(staging, missing_ok=True)
                except OSError:
                    pass
                raise
        self._update_index(record)
        return self._with_active(record)

    def list_packages(self) -> tuple[OperatorCalibrationPackageRecord, ...]:
        if not self.index_path.exists():
            return ()
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ()
        active = self.active_fingerprint()
        records: list[OperatorCalibrationPackageRecord] = []
        for item in payload.get("packages", []):
            try:
                records.append(self._record_from_dict(item, active=item.get("package_fingerprint") == active))
            except (TypeError, ValueError, KeyError):
                continue
        return tuple(sorted(records, key=lambda item: (item.package_id, item.version, item.imported_at)))

    def activate_package(self, package_fingerprint: str) -> OperatorCalibrationPackageRecord:
        record = self.get_package(package_fingerprint)
        payload = {
            "schema": self.ACTIVE_SCHEMA,
            "project_id": self.project_id,
            "package_id": record.package_id,
            "version": record.version,
            "package_fingerprint": record.package_fingerprint,
            "activated_at": self._utc_now(),
        }
        self._atomic_write_json(self.active_path, payload)
        return self._with_active(record, active=True)

    def deactivate_package(self) -> None:
        self.delete_engine.delete_path(self.active_path, missing_ok=True)

    def active_fingerprint(self) -> str:
        if not self.active_path.exists():
            return ""
        try:
            payload = json.loads(self.active_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ""
        if payload.get("schema") != self.ACTIVE_SCHEMA or payload.get("project_id") != self.project_id:
            return ""
        return str(payload.get("package_fingerprint", ""))

    def active_package(self) -> OperatorCalibrationPackageRecord | None:
        fingerprint = self.active_fingerprint()
        if not fingerprint:
            return None
        try:
            return self.get_package(fingerprint, active=True)
        except KeyError:
            return None

    def get_package(self, package_fingerprint: str, *, active: bool | None = None) -> OperatorCalibrationPackageRecord:
        clean = str(package_fingerprint).strip().lower()
        for record in self.list_packages():
            if record.package_fingerprint == clean:
                path = self.project_root / record.storage_path / PACKAGE_MANIFEST_NAME
                manifest = json.loads(path.read_text(encoding="utf-8"))
                method_registry = load_petrophysical_method_registry(
                    self.application_root / "config" / "petrophysical_method_registry_v225_9.json"
                )
                errors = validate_operator_package_manifest(
                    manifest,
                    project_id=self.project_id,
                    expected_method_registry_fingerprint=contract_fingerprint(method_registry),
                )
                if errors:
                    raise OperatorCalibrationPackageError("; ".join(errors))
                self._validate_stored_package(record, manifest)
                return self._with_active(record, active=self.active_fingerprint() == clean if active is None else active)
        raise KeyError(f"operator calibration package not found: {clean}")

    def compare(
        self,
        target_fingerprint: str,
        *,
        reference_fingerprint: str | None = None,
        persist: bool = True,
    ) -> OperatorCalibrationComparisonReport:
        target_record = self.get_package(target_fingerprint)
        target_report = self._run_package_gate(target_record)
        if reference_fingerprint:
            reference_record = self.get_package(reference_fingerprint)
            reference_report = self._run_package_gate(reference_record)
            reference_kind = "operator_package"
            reference_label = reference_record.package_fingerprint
        else:
            reference_report = self.baseline_calibration_service.run_gate()
            reference_report.assert_passed()
            reference_kind = "project_baseline"
            reference_label = reference_report.contract_fingerprint

        reference = self._aggregate_report(reference_report)
        target = self._aggregate_report(target_report)
        rows: list[CalibrationComparisonMethod] = []
        for method_id in sorted(set(reference) | set(target)):
            left = reference.get(method_id)
            right = target.get(method_id)
            if left is None:
                status = "target_only"
            elif right is None:
                status = "reference_only"
            elif right.passed and not left.passed:
                status = "improved"
            elif left.passed and not right.passed:
                status = "degraded"
            else:
                delta = right.rmse - left.rmse
                status = "equivalent" if abs(delta) <= 1e-12 else ("improved" if delta < 0 else "degraded")
            rows.append(
                CalibrationComparisonMethod(
                    method_id=method_id,
                    status=status,
                    reference_source=reference_kind,
                    target_source="operator_package",
                    reference_passed=None if left is None else left.passed,
                    target_passed=None if right is None else right.passed,
                    reference_rmse=None if left is None else left.rmse,
                    target_rmse=None if right is None else right.rmse,
                    rmse_delta=None if left is None or right is None else right.rmse - left.rmse,
                    reference_max_abs_error=None if left is None else left.max_abs_error,
                    target_max_abs_error=None if right is None else right.max_abs_error,
                    max_abs_error_delta=None if left is None or right is None else right.max_abs_error - left.max_abs_error,
                    reference_uncertainty_width=None if left is None else left.max_uncertainty_width,
                    target_uncertainty_width=None if right is None else right.max_uncertainty_width,
                    uncertainty_width_delta=None if left is None or right is None else right.max_uncertainty_width - left.max_uncertainty_width,
                )
            )
        deterministic = {
            "project_id": self.project_id,
            "reference_kind": reference_kind,
            "reference_fingerprint": reference_label,
            "target_fingerprint": target_record.package_fingerprint,
            "reference_gate_id": reference_report.gate_id,
            "target_gate_id": target_report.gate_id,
            "methods": [asdict(item) for item in rows],
        }
        comparison_id = "cmp-" + sha256(canonical_json_bytes(deterministic)).hexdigest()[:20]
        report = OperatorCalibrationComparisonReport(
            schema=OPERATOR_CALIBRATION_COMPARISON_SCHEMA,
            generated_at=self._utc_now(),
            comparison_id=comparison_id,
            project_id=self.project_id,
            reference_kind=reference_kind,
            reference_fingerprint=reference_label,
            target_fingerprint=target_record.package_fingerprint,
            reference_gate_id=reference_report.gate_id,
            target_gate_id=target_report.gate_id,
            passed=target_report.passed,
            methods=tuple(rows),
        )
        if persist:
            self._atomic_write_json(self.comparisons_root / f"{comparison_id}.json", report.to_dict())
        return report

    def issue_authorization_package(
        self,
        method_ids: Sequence[str],
        *,
        package_fingerprint: str | None = None,
        final_report: bool = True,
    ) -> ProjectPetrophysicalAuthorizationPackage:
        requested = tuple(dict.fromkeys(str(item).strip() for item in method_ids if str(item).strip()))
        if not requested:
            raise ValueError("At least one petrophysical method is required")
        record = self.get_package(package_fingerprint or self.active_fingerprint())
        target_report = self._run_package_gate(record)
        baseline_report = self.baseline_calibration_service.run_gate()
        baseline_report.assert_passed()
        comparison = self.compare(record.package_fingerprint, persist=True)
        validation = self.validation_service.authorize_methods(requested, final_report=False)
        validation_by_id = {item.method_id: item for item in validation.methods}
        target_by_id = self._aggregate_report(target_report)
        baseline_by_id = self._aggregate_report(baseline_report)
        manifest = self._load_manifest(record)
        rights = manifest["rights"]
        rights_allowed = bool(rights.get("final_report_use_allowed", False)) if final_report else bool(rights.get("processing_allowed", False))
        methods: list[ProjectMethodAuthorization] = []
        warnings: list[str] = []
        for method_id in requested:
            validation_item = validation_by_id[method_id]
            operator_item = target_by_id.get(method_id)
            calibration_item = operator_item or baseline_by_id.get(method_id)
            source = "operator" if operator_item is not None else "baseline"
            reasons: list[str] = []
            if not validation_item.passed:
                reasons.append("numerical_validation_failed")
            if final_report and not validation_item.final_report_eligible:
                reasons.append("report_policy_blocked")
            if calibration_item is None:
                reasons.append("calibration_missing")
            elif not calibration_item.passed:
                reasons.append("calibration_failed")
            elif final_report and calibration_item.calibration_policy == "required_final_report" and not calibration_item.final_report_calibrated:
                reasons.append("final_report_calibration_missing")
            if source == "operator" and not rights_allowed:
                reasons.append("operator_data_rights_block_final_report" if final_report else "operator_data_rights_block_processing")
            if validation_item.report_policy == "allowed_with_warning":
                warnings.append(f"{method_id}: allowed_with_warning")
            methods.append(
                ProjectMethodAuthorization(
                    method_id=method_id,
                    calibration_source=source,
                    numerical_validation_passed=validation_item.passed,
                    calibration_passed=bool(calibration_item and calibration_item.passed),
                    report_policy=validation_item.report_policy,
                    rights_allowed=rights_allowed if source == "operator" else True,
                    authorized=not reasons,
                    reasons=tuple(reasons),
                )
            )
        deterministic = {
            "project_id": self.project_id,
            "final_report": bool(final_report),
            "method_ids": requested,
            "validation_gate_id": validation.gate_id,
            "baseline_calibration_gate_id": baseline_report.gate_id,
            "operator_calibration_gate_id": target_report.gate_id,
            "comparison_id": comparison.comparison_id,
            "operator_package_fingerprint": record.package_fingerprint,
            "rights_fingerprint": record.rights_fingerprint,
            "methods": [asdict(item) for item in methods],
        }
        digest = sha256(canonical_json_bytes(deterministic)).hexdigest()
        authorization_id = "authp-" + digest[:20]
        authorization_package_id = "papa-" + digest[20:40]
        package = ProjectPetrophysicalAuthorizationPackage(
            schema=PROJECT_AUTHORIZATION_PACKAGE_SCHEMA,
            generated_at=self._utc_now(),
            authorization_id=authorization_id,
            authorization_package_id=authorization_package_id,
            project_id=self.project_id,
            final_report=bool(final_report),
            passed=all(item.authorized for item in methods),
            method_ids=requested,
            validation_gate_id=validation.gate_id,
            calibration_gate_id=target_report.gate_id,
            baseline_calibration_gate_id=baseline_report.gate_id,
            comparison_id=comparison.comparison_id,
            operator_package_id=record.package_id,
            operator_package_version=record.version,
            operator_package_fingerprint=record.package_fingerprint,
            rights_fingerprint=record.rights_fingerprint,
            validation_contract_fingerprint=validation.contract_fingerprint,
            calibration_contract_fingerprint=target_report.contract_fingerprint,
            methods=tuple(methods),
            warnings=tuple(dict.fromkeys(warnings)),
        )
        destination = self.authorizations_root / record.package_id / record.version / f"{authorization_package_id}.json"
        self._atomic_write_json(destination, package.to_dict())
        return package

    def authorize_methods_for_export(
        self,
        method_ids: Sequence[str],
        *,
        final_report: bool = True,
    ) -> Any:
        """Use the active project package, or Stage 5.1 baseline when none exists."""
        active = self.active_package()
        if active is None:
            return self.baseline_authorization_service.authorize(method_ids, final_report=final_report)
        return self.issue_authorization_package(
            method_ids,
            package_fingerprint=active.package_fingerprint,
            final_report=final_report,
        )

    def _run_package_gate(self, record: OperatorCalibrationPackageRecord) -> PetrophysicalCalibrationReport:
        root = self.project_root / record.storage_path
        service = PetrophysicalCalibrationApplicationService(
            root=self.application_root,
            registry_path=root / PACKAGE_REGISTRY_NAME,
            dataset_path=root / PACKAGE_DATASET_NAME,
            validation_service=self.validation_service,
            require_redistribution_allowed=False,
        )
        report = service.run_gate()
        report.assert_passed()
        return report

    def _load_manifest(self, record: OperatorCalibrationPackageRecord) -> dict[str, Any]:
        return json.loads((self.project_root / record.storage_path / PACKAGE_MANIFEST_NAME).read_text(encoding="utf-8"))

    def _validate_stored_package(
        self,
        record: OperatorCalibrationPackageRecord,
        manifest: Mapping[str, Any],
    ) -> None:
        package_root = self.project_root / record.storage_path
        if str(manifest.get("package_fingerprint", "")) != record.package_fingerprint:
            raise OperatorCalibrationPackageError("stored package fingerprint differs from import record")
        if operator_package_fingerprint(manifest) != record.package_fingerprint:
            raise OperatorCalibrationPackageError("stored manifest fingerprint mismatch")
        if rights_fingerprint(manifest.get("rights", {})) != record.rights_fingerprint:
            raise OperatorCalibrationPackageError("stored data-rights fingerprint mismatch")
        files = manifest.get("files", {})
        for name in (PACKAGE_REGISTRY_NAME, PACKAGE_DATASET_NAME):
            path = package_root / name
            try:
                payload = path.read_bytes()
            except OSError as exc:
                raise OperatorCalibrationPackageError(f"stored package file is missing: {name}") from exc
            file_record = files.get(name, {}) if isinstance(files, Mapping) else {}
            expected_digest = str(file_record.get("sha256", "")).lower()
            try:
                expected_size = int(file_record.get("size_bytes", -1))
            except (TypeError, ValueError) as exc:
                raise OperatorCalibrationPackageError(f"stored manifest size is invalid: {name}") from exc
            if sha256_hex(payload) != expected_digest or len(payload) != expected_size:
                raise OperatorCalibrationPackageError(f"stored package content was modified: {name}")

    @staticmethod
    def _aggregate_report(report: PetrophysicalCalibrationReport) -> dict[str, MethodCalibrationAggregate]:
        grouped: dict[str, list[MethodCalibrationResult]] = {}
        for item in report.methods:
            grouped.setdefault(item.method_id, []).append(item)
        aggregates: dict[str, MethodCalibrationAggregate] = {}
        for method_id, items in grouped.items():
            total_outputs = sum(max(0, item.metrics.count) for item in items)
            divisor = max(total_outputs, 1)
            rmse = math.sqrt(
                sum((item.metrics.rmse ** 2) * max(0, item.metrics.count) for item in items) / divisor
            )
            aggregates[method_id] = MethodCalibrationAggregate(
                method_id=method_id,
                case_count=len(items),
                output_count=total_outputs,
                passed=all(item.passed for item in items),
                final_report_calibrated=all(item.final_report_calibrated for item in items),
                calibration_policy=items[0].calibration_policy,
                rmse=rmse,
                mae=sum(item.metrics.mae * max(0, item.metrics.count) for item in items) / divisor,
                max_abs_error=max(item.metrics.max_abs_error for item in items),
                bias=sum(item.metrics.bias * max(0, item.metrics.count) for item in items) / divisor,
                max_uncertainty_width=max(item.uncertainty_envelope.max_width for item in items),
                mean_uncertainty_width=sum(item.uncertainty_envelope.mean_width for item in items) / len(items),
            )
        return aggregates

    def _decode_package(self, package_bytes: bytes) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, bytes]]:
        try:
            with ZipFile(BytesIO(package_bytes), "r") as archive:
                infos = archive.infolist()
                names = [item.filename for item in infos if not item.is_dir()]
                if sorted(names) != sorted(PACKAGE_FILE_NAMES):
                    raise OperatorCalibrationPackageError(
                        "operator package must contain exactly manifest.json, calibration_registry.json and calibration_dataset.json"
                    )
                for info in infos:
                    name = info.filename
                    if info.is_dir():
                        raise OperatorCalibrationPackageError("operator package cannot contain directories")
                    if Path(name).name != name or name.startswith(("/", "\\")) or ".." in Path(name).parts:
                        raise OperatorCalibrationPackageError(f"unsafe ZIP member: {name}")
                    if info.file_size <= 0 or info.file_size > self.MAX_MEMBER_BYTES:
                        raise OperatorCalibrationPackageError(f"invalid ZIP member size: {name}")
                raw = {name: archive.read(name) for name in PACKAGE_FILE_NAMES}
        except BadZipFile as exc:
            raise OperatorCalibrationPackageError("operator calibration package is not a valid ZIP archive") from exc

        try:
            manifest = json.loads(raw[PACKAGE_MANIFEST_NAME].decode("utf-8"))
            registry = json.loads(raw[PACKAGE_REGISTRY_NAME].decode("utf-8"))
            dataset = json.loads(raw[PACKAGE_DATASET_NAME].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OperatorCalibrationPackageError("operator package JSON is invalid UTF-8/JSON") from exc
        if not all(isinstance(item, dict) for item in (manifest, registry, dataset)):
            raise OperatorCalibrationPackageError("operator package JSON roots must be objects")
        files = manifest.get("files", {})
        for name in (PACKAGE_REGISTRY_NAME, PACKAGE_DATASET_NAME):
            record = files.get(name, {}) if isinstance(files, Mapping) else {}
            if sha256_hex(raw[name]) != str(record.get("sha256", "")).lower():
                raise OperatorCalibrationPackageError(f"checksum mismatch: {name}")
            try:
                declared_size = int(record.get("size_bytes", -1))
            except (TypeError, ValueError) as exc:
                raise OperatorCalibrationPackageError(f"invalid declared size: {name}") from exc
            if len(raw[name]) != declared_size:
                raise OperatorCalibrationPackageError(f"size mismatch: {name}")
        if operator_package_fingerprint(manifest) != str(manifest.get("package_fingerprint", "")):
            raise OperatorCalibrationPackageError("package fingerprint mismatch")
        return manifest, registry, dataset, raw

    def _read_source(self, source: bytes | bytearray | Path | str) -> bytes:
        if isinstance(source, (bytes, bytearray)):
            payload = bytes(source)
        else:
            payload = Path(source).read_bytes()
        if not payload or len(payload) > self.MAX_PACKAGE_BYTES:
            raise OperatorCalibrationPackageError("operator package size is outside the supported range")
        return payload

    def _update_index(self, record: OperatorCalibrationPackageRecord) -> None:
        records = {item.package_fingerprint: item for item in self.list_packages()}
        records[record.package_fingerprint] = record
        payload = {
            "schema": self.INDEX_SCHEMA,
            "project_id": self.project_id,
            "updated_at": self._utc_now(),
            "packages": [item.to_dict() for item in sorted(records.values(), key=lambda x: (x.package_id, x.version, x.imported_at))],
        }
        self._atomic_write_json(self.index_path, payload)

    def _load_record(self, path: Path) -> OperatorCalibrationPackageRecord:
        return self._record_from_dict(json.loads(path.read_text(encoding="utf-8")), active=False)

    @staticmethod
    def _record_from_dict(payload: Mapping[str, Any], *, active: bool) -> OperatorCalibrationPackageRecord:
        return OperatorCalibrationPackageRecord(
            schema=str(payload["schema"]),
            project_id=str(payload["project_id"]),
            package_id=str(payload["package_id"]),
            version=str(payload["version"]),
            package_fingerprint=str(payload["package_fingerprint"]),
            rights_fingerprint=str(payload["rights_fingerprint"]),
            imported_at=str(payload["imported_at"]),
            operator_name=str(payload["operator_name"]),
            legal_status=str(payload["legal_status"]),
            data_classification=str(payload["data_classification"]),
            final_report_use_allowed=bool(payload["final_report_use_allowed"]),
            redistribution_allowed=bool(payload["redistribution_allowed"]),
            method_ids=tuple(str(item) for item in payload.get("method_ids", ())),
            calibration_gate_id=str(payload["calibration_gate_id"]),
            calibration_contract_fingerprint=str(payload["calibration_contract_fingerprint"]),
            storage_path=str(payload["storage_path"]),
            active=bool(active),
        )

    @staticmethod
    def _with_active(
        record: OperatorCalibrationPackageRecord,
        *,
        active: bool | None = None,
    ) -> OperatorCalibrationPackageRecord:
        desired = record.active if active is None else bool(active)
        if desired == record.active:
            return record
        payload = record.to_dict()
        payload["active"] = desired
        return OperatorCalibrationPackageApplicationService._record_from_dict(payload, active=desired)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
