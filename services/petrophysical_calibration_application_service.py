"""Stage 5.1 field calibration, sensitivity and uncertainty diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.petrophysical_calibration_contract import (
    FIELD_CALIBRATION_GATE_SCHEMA,
    calibration_contract_fingerprint,
    load_field_calibration_dataset,
    load_field_calibration_registry,
    validate_field_calibration_contract,
)
from core.petrophysical_method_executor import execute_petrophysical_method
from core.petrophysical_validation_contract import load_petrophysical_method_registry
from services.petrophysical_validation_application_service import PetrophysicalValidationApplicationService


@dataclass(frozen=True, slots=True)
class CalibrationMetrics:
    count: int
    rmse: float
    mae: float
    max_abs_error: float
    bias: float


@dataclass(frozen=True, slots=True)
class ParameterSensitivityResult:
    parameter: str
    unit: str
    distribution: str
    low: float
    mode: float
    high: float
    output_count: int
    max_abs_shift: float
    mean_abs_shift: float
    increasing_count: int
    decreasing_count: int


@dataclass(frozen=True, slots=True)
class UncertaintyEnvelope:
    strategy: str
    output_paths: tuple[str, ...]
    lower: tuple[float, ...]
    base: tuple[float, ...]
    upper: tuple[float, ...]
    max_width: float
    mean_width: float


@dataclass(frozen=True, slots=True)
class MethodCalibrationResult:
    method_id: str
    case_id: str
    calibration_id: str
    calibration_policy: str
    passed: bool
    final_report_calibrated: bool
    metrics: CalibrationMetrics
    acceptance: Mapping[str, float]
    sensitivity: tuple[ParameterSensitivityResult, ...]
    uncertainty_envelope: UncertaintyEnvelope
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PetrophysicalCalibrationReport:
    schema: str
    generated_at: str
    gate_id: str
    contract_fingerprint: str
    validation_gate_id: str
    registry_version: str
    dataset_version: str
    passed: bool
    structural_errors: tuple[str, ...]
    methods: tuple[MethodCalibrationResult, ...]

    @property
    def calibrated_method_count(self) -> int:
        return sum(item.passed for item in self.methods)

    @property
    def final_report_calibrated_count(self) -> int:
        return sum(item.passed and item.final_report_calibrated for item in self.methods)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["calibrated_method_count"] = self.calibrated_method_count
        payload["final_report_calibrated_count"] = self.final_report_calibrated_count
        return payload

    def assert_passed(self) -> None:
        if not self.passed:
            details = "; ".join(self.structural_errors) or "field calibration mismatch"
            raise RuntimeError(f"Petrophysical field calibration gate failed: {details}")


class PetrophysicalCalibrationApplicationService:
    """Run legally-cleared calibration cases through production methods."""

    def __init__(
        self,
        *,
        root: Path | str,
        registry_path: Path | str | None = None,
        dataset_path: Path | str | None = None,
        validation_service: PetrophysicalValidationApplicationService | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.registry_path = Path(registry_path).resolve() if registry_path else self.root / "config" / "petrophysical_field_calibration_registry_v225_10.json"
        self.dataset_path = Path(dataset_path).resolve() if dataset_path else self.root / "data" / "validation" / "petrophysics" / "petrophysical_field_calibration_cases_v225_10.json"
        self.validation_service = validation_service or PetrophysicalValidationApplicationService(root=self.root)

    def run_gate(self) -> PetrophysicalCalibrationReport:
        validation_report = self.validation_service.run_gate()
        validation_report.assert_passed()
        method_registry = load_petrophysical_method_registry(self.validation_service.registry_path)
        registry = load_field_calibration_registry(self.registry_path)
        dataset = load_field_calibration_dataset(self.dataset_path)
        known_ids = {str(item["method_id"]) for item in method_registry.get("methods", [])}
        structural_errors = validate_field_calibration_contract(registry, dataset, known_method_ids=known_ids)
        cases_by_id = {str(item["case_id"]): item for item in dataset.get("cases", [])}
        results: list[MethodCalibrationResult] = []
        if not structural_errors:
            for record in registry["methods"]:
                for case_id in record["case_ids"]:
                    results.append(self._calibrate_case(record, cases_by_id[str(case_id)]))

        fingerprint = calibration_contract_fingerprint(method_registry, registry, dataset)
        deterministic = {
            "contract_fingerprint": fingerprint,
            "validation_gate_id": validation_report.gate_id,
            "structural_errors": list(structural_errors),
            "methods": [asdict(item) for item in results],
        }
        gate_id = "cal-" + sha256(
            json.dumps(deterministic, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:20]
        passed = not structural_errors and bool(results) and all(item.passed for item in results)
        return PetrophysicalCalibrationReport(
            schema=FIELD_CALIBRATION_GATE_SCHEMA,
            generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            gate_id=gate_id,
            contract_fingerprint=fingerprint,
            validation_gate_id=validation_report.gate_id,
            registry_version=str(registry["version"]),
            dataset_version=str(dataset["version"]),
            passed=passed,
            structural_errors=tuple(structural_errors),
            methods=tuple(results),
        )

    def authorize_methods(self, method_ids: Sequence[str]) -> PetrophysicalCalibrationReport:
        requested = tuple(dict.fromkeys(str(item) for item in method_ids))
        report = self.run_gate()
        report.assert_passed()
        by_id = {item.method_id: item for item in report.methods}
        missing = [item for item in requested if item not in by_id]
        if missing:
            raise KeyError("Methods are not covered by field calibration: " + ", ".join(missing))
        failed = [item for item in requested if not by_id[item].passed]
        if failed:
            raise RuntimeError("Methods failed field calibration: " + ", ".join(failed))
        required_not_calibrated = [
            item for item in requested
            if by_id[item].calibration_policy == "required_final_report" and not by_id[item].final_report_calibrated
        ]
        if required_not_calibrated:
            raise PermissionError("Methods are not calibrated for final reports: " + ", ".join(required_not_calibrated))
        return report

    def write_evidence(self, path: Path | str) -> PetrophysicalCalibrationReport:
        report = self.run_gate()
        destination = Path(path)
        if not destination.is_absolute():
            destination = self.root / destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(destination)
        return report

    def _calibrate_case(self, record: Mapping[str, Any], case: Mapping[str, Any]) -> MethodCalibrationResult:
        method_id = str(record["method_id"])
        base_parameters = dict(case.get("parameters", {}))
        base_output = execute_petrophysical_method(
            method_id,
            inputs=case.get("inputs", {}),
            parameters=base_parameters,
        )
        paths, predicted = self._numeric_leaves(base_output)
        observed_paths, observed = self._numeric_leaves(case.get("observed", {}))
        diagnostics: list[str] = []
        if paths != observed_paths:
            diagnostics.append("predicted and observed output paths differ")
        common = min(len(predicted), len(observed))
        errors = [predicted[index] - observed[index] for index in range(common)]
        metrics = self._metrics(errors)
        acceptance = {key: float(value) for key, value in record["acceptance"].items()}
        passed = (
            paths == observed_paths
            and metrics.count > 0
            and metrics.rmse <= acceptance["max_rmse"]
            and metrics.mae <= acceptance["max_mae"]
            and metrics.max_abs_error <= acceptance["max_abs_error"]
            and abs(metrics.bias) <= acceptance["max_abs_bias"]
        )

        all_outputs: list[list[float]] = [predicted]
        sensitivity: list[ParameterSensitivityResult] = []
        for distribution in record.get("parameter_distributions", []):
            name = str(distribution["name"])
            low_params = dict(base_parameters)
            high_params = dict(base_parameters)
            low_params[name] = float(distribution["low"])
            high_params[name] = float(distribution["high"])
            low_paths, low_values = self._numeric_leaves(execute_petrophysical_method(method_id, inputs=case["inputs"], parameters=low_params))
            high_paths, high_values = self._numeric_leaves(execute_petrophysical_method(method_id, inputs=case["inputs"], parameters=high_params))
            if low_paths != paths or high_paths != paths:
                diagnostics.append(f"sensitivity output paths differ for parameter {name}")
                passed = False
                continue
            all_outputs.extend((low_values, high_values))
            shifts = [max(abs(low_values[i] - predicted[i]), abs(high_values[i] - predicted[i])) for i in range(len(predicted))]
            deltas = [high_values[i] - low_values[i] for i in range(len(predicted))]
            sensitivity.append(
                ParameterSensitivityResult(
                    parameter=name,
                    unit=str(distribution.get("unit", "1")),
                    distribution=str(distribution["distribution"]),
                    low=float(distribution["low"]),
                    mode=float(distribution["mode"]),
                    high=float(distribution["high"]),
                    output_count=len(predicted),
                    max_abs_shift=max(shifts, default=0.0),
                    mean_abs_shift=sum(shifts) / len(shifts) if shifts else 0.0,
                    increasing_count=sum(delta > 0 for delta in deltas),
                    decreasing_count=sum(delta < 0 for delta in deltas),
                )
            )

        lower = tuple(min(values[index] for values in all_outputs) for index in range(len(predicted)))
        upper = tuple(max(values[index] for values in all_outputs) for index in range(len(predicted)))
        widths = [upper[index] - lower[index] for index in range(len(predicted))]
        uncertainty = UncertaintyEnvelope(
            strategy=str(record.get("uncertainty", {}).get("strategy", "one_at_a_time_envelope")),
            output_paths=tuple(paths),
            lower=lower,
            base=tuple(predicted),
            upper=upper,
            max_width=max(widths, default=0.0),
            mean_width=sum(widths) / len(widths) if widths else 0.0,
        )
        policy = str(record["calibration_policy"])
        return MethodCalibrationResult(
            method_id=method_id,
            case_id=str(case["case_id"]),
            calibration_id=str(case["calibration_id"]),
            calibration_policy=policy,
            passed=passed,
            final_report_calibrated=passed and policy == "required_final_report",
            metrics=metrics,
            acceptance=acceptance,
            sensitivity=tuple(sensitivity),
            uncertainty_envelope=uncertainty,
            diagnostics=tuple(diagnostics),
        )

    @staticmethod
    def _numeric_leaves(payload: Any, path: str = "$") -> tuple[list[str], list[float]]:
        paths: list[str] = []
        values: list[float] = []

        def visit(value: Any, current: str) -> None:
            if isinstance(value, Mapping):
                for key in sorted(value):
                    visit(value[key], f"{current}.{key}")
            elif isinstance(value, (list, tuple)):
                for index, item in enumerate(value):
                    visit(item, f"{current}[{index}]")
            elif value is None:
                return
            elif isinstance(value, (int, float)) and math.isfinite(float(value)):
                paths.append(current)
                values.append(float(value))
            else:
                raise TypeError(f"Non-numeric calibration output at {current}: {value!r}")

        visit(payload, path)
        return paths, values

    @staticmethod
    def _metrics(errors: Sequence[float]) -> CalibrationMetrics:
        values = [float(item) for item in errors]
        if not values:
            return CalibrationMetrics(0, math.inf, math.inf, math.inf, math.inf)
        return CalibrationMetrics(
            count=len(values),
            rmse=math.sqrt(sum(value * value for value in values) / len(values)),
            mae=sum(abs(value) for value in values) / len(values),
            max_abs_error=max(abs(value) for value in values),
            bias=sum(values) / len(values),
        )
