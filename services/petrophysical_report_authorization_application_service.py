"""Final-report authorization boundary for petrophysical methods."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Sequence

from core.petrophysical_calibration_contract import REPORT_AUTHORIZATION_SCHEMA
from services.petrophysical_calibration_application_service import PetrophysicalCalibrationApplicationService
from services.petrophysical_validation_application_service import PetrophysicalValidationApplicationService


@dataclass(frozen=True, slots=True)
class MethodReportAuthorization:
    method_id: str
    numerical_validation_passed: bool
    calibration_passed: bool
    calibration_required: bool
    report_policy: str
    authorized: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PetrophysicalReportAuthorization:
    schema: str
    generated_at: str
    authorization_id: str
    final_report: bool
    passed: bool
    method_ids: tuple[str, ...]
    validation_gate_id: str
    calibration_gate_id: str
    validation_contract_fingerprint: str
    calibration_contract_fingerprint: str
    methods: tuple[MethodReportAuthorization, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def assert_authorized(self) -> None:
        if not self.passed:
            blocked = [item.method_id for item in self.methods if not item.authorized]
            raise PermissionError("Petrophysical final-report authorization failed: " + ", ".join(blocked))


class PetrophysicalReportAuthorizationApplicationService:
    """Combine numerical validation, field calibration and report policy."""

    def __init__(
        self,
        *,
        root: Path | str,
        validation_service: PetrophysicalValidationApplicationService | None = None,
        calibration_service: PetrophysicalCalibrationApplicationService | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.validation_service = validation_service or PetrophysicalValidationApplicationService(root=self.root)
        self.calibration_service = calibration_service or PetrophysicalCalibrationApplicationService(
            root=self.root,
            validation_service=self.validation_service,
        )

    def authorize(
        self,
        method_ids: Sequence[str],
        *,
        final_report: bool = True,
    ) -> PetrophysicalReportAuthorization:
        requested = tuple(dict.fromkeys(str(item).strip() for item in method_ids if str(item).strip()))
        if not requested:
            raise ValueError("At least one petrophysical method is required for report authorization")
        validation = self.validation_service.authorize_methods(requested, final_report=False)
        calibration = self.calibration_service.run_gate()
        calibration.assert_passed()
        validation_by_id = {item.method_id: item for item in validation.methods}
        calibration_by_id = {item.method_id: item for item in calibration.methods}
        methods: list[MethodReportAuthorization] = []
        warnings: list[str] = []
        for method_id in requested:
            v = validation_by_id[method_id]
            c = calibration_by_id.get(method_id)
            reasons: list[str] = []
            calibration_required = bool(c and c.calibration_policy == "required_final_report")
            calibration_passed = bool(c and c.passed)
            if not v.passed:
                reasons.append("numerical_validation_failed")
            if final_report and not v.final_report_eligible:
                reasons.append("report_policy_blocked")
            if c is None:
                reasons.append("field_calibration_missing")
            elif not c.passed:
                reasons.append("field_calibration_failed")
            elif final_report and calibration_required and not c.final_report_calibrated:
                reasons.append("final_report_calibration_missing")
            if v.report_policy == "allowed_with_warning":
                warnings.append(f"{method_id}: allowed_with_warning")
            authorized = not reasons
            methods.append(
                MethodReportAuthorization(
                    method_id=method_id,
                    numerical_validation_passed=v.passed,
                    calibration_passed=calibration_passed,
                    calibration_required=calibration_required,
                    report_policy=v.report_policy,
                    authorized=authorized,
                    reasons=tuple(reasons),
                )
            )
        deterministic = {
            "final_report": bool(final_report),
            "method_ids": requested,
            "validation_gate_id": validation.gate_id,
            "calibration_gate_id": calibration.gate_id,
            "methods": [asdict(item) for item in methods],
        }
        authorization_id = "auth-" + sha256(
            json.dumps(deterministic, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:20]
        return PetrophysicalReportAuthorization(
            schema=REPORT_AUTHORIZATION_SCHEMA,
            generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            authorization_id=authorization_id,
            final_report=bool(final_report),
            passed=all(item.authorized for item in methods),
            method_ids=requested,
            validation_gate_id=validation.gate_id,
            calibration_gate_id=calibration.gate_id,
            validation_contract_fingerprint=validation.contract_fingerprint,
            calibration_contract_fingerprint=calibration.contract_fingerprint,
            methods=tuple(methods),
            warnings=tuple(dict.fromkeys(warnings)),
        )

    def write_evidence(
        self,
        method_ids: Sequence[str],
        path: Path | str,
        *,
        final_report: bool = True,
    ) -> PetrophysicalReportAuthorization:
        authorization = self.authorize(method_ids, final_report=final_report)
        destination = Path(path)
        if not destination.is_absolute():
            destination = self.root / destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(json.dumps(authorization.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(destination)
        return authorization
