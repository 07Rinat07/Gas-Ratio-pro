"""Application-service validation gate for the frozen petrophysical engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from core.petrophysical_validation_contract import (
    PETROPHYSICAL_VALIDATION_GATE_SCHEMA,
    contract_fingerprint,
    load_petrophysical_method_registry,
    load_petrophysical_validation_dataset,
    validate_registry_contract,
)
from las_editor.advanced_saturation_models import (
    DualWaterParameters,
    ShalySandParameters,
    calculate_dual_water_saturation,
    calculate_indonesia_water_saturation,
    calculate_simandoux_water_saturation,
)
from las_editor.petrophysical_workspace import (
    ArchieParameters,
    PetrophysicalCutoffSet,
    ShaleVolumeParameters,
    calculate_archie_water_saturation,
    calculate_effective_porosity,
    calculate_net_pay_flags,
    calculate_shale_volume,
)


@dataclass(frozen=True, slots=True)
class ValidationMismatch:
    path: str
    expected: Any
    actual: Any
    absolute_error: float | None = None
    tolerance: float | None = None


@dataclass(frozen=True, slots=True)
class MethodValidationResult:
    method_id: str
    case_id: str
    passed: bool
    report_policy: str
    final_report_eligible: bool
    absolute_tolerance: float
    relative_tolerance: float
    mismatches: tuple[ValidationMismatch, ...] = ()


@dataclass(frozen=True, slots=True)
class PetrophysicalValidationReport:
    schema: str
    generated_at: str
    gate_id: str
    contract_fingerprint: str
    registry_version: str
    dataset_version: str
    passed: bool
    structural_errors: tuple[str, ...]
    methods: tuple[MethodValidationResult, ...]

    @property
    def validated_method_count(self) -> int:
        return sum(item.passed for item in self.methods)

    @property
    def final_report_eligible_count(self) -> int:
        return sum(item.passed and item.final_report_eligible for item in self.methods)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["validated_method_count"] = self.validated_method_count
        payload["final_report_eligible_count"] = self.final_report_eligible_count
        return payload

    def assert_passed(self) -> None:
        if not self.passed:
            details = "; ".join(self.structural_errors) or "numerical validation mismatch"
            raise RuntimeError(f"Petrophysical validation gate failed: {details}")


class PetrophysicalValidationApplicationService:
    """Execute production formulas against static synthetic reference cases."""

    def __init__(
        self,
        *,
        root: Path | str,
        registry_path: Path | str | None = None,
        dataset_path: Path | str | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.registry_path = Path(registry_path).resolve() if registry_path else self.root / "config" / "petrophysical_method_registry_v225_9.json"
        self.dataset_path = Path(dataset_path).resolve() if dataset_path else self.root / "data" / "validation" / "petrophysics" / "petrophysical_validation_cases_v225_9.json"

    def run_gate(self) -> PetrophysicalValidationReport:
        registry = load_petrophysical_method_registry(self.registry_path)
        dataset = load_petrophysical_validation_dataset(self.dataset_path)
        structural_errors = validate_registry_contract(registry, dataset)
        methods_by_id = {item["method_id"]: item for item in registry.get("methods", [])}
        results: list[MethodValidationResult] = []
        if not structural_errors:
            for case in dataset["cases"]:
                method = methods_by_id[case["method_id"]]
                results.append(self._validate_case(method, case))

        fingerprint = contract_fingerprint(registry, dataset)
        deterministic = {
            "contract_fingerprint": fingerprint,
            "structural_errors": list(structural_errors),
            "methods": [asdict(item) for item in results],
        }
        gate_id = "petro-" + sha256(
            json.dumps(deterministic, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:20]
        passed = not structural_errors and bool(results) and all(item.passed for item in results)
        return PetrophysicalValidationReport(
            schema=PETROPHYSICAL_VALIDATION_GATE_SCHEMA,
            generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            gate_id=gate_id,
            contract_fingerprint=fingerprint,
            registry_version=str(registry["version"]),
            dataset_version=str(dataset["version"]),
            passed=passed,
            structural_errors=tuple(structural_errors),
            methods=tuple(results),
        )

    def authorize_methods(
        self,
        method_ids: Sequence[str],
        *,
        final_report: bool = False,
    ) -> PetrophysicalValidationReport:
        """Validate selected methods and enforce final-report policy when requested."""

        requested = tuple(dict.fromkeys(str(item) for item in method_ids))
        report = self.run_gate()
        report.assert_passed()
        by_id = {item.method_id: item for item in report.methods}
        missing = [item for item in requested if item not in by_id]
        if missing:
            raise KeyError(f"Methods are not covered by the validation gate: {', '.join(missing)}")
        failed = [item for item in requested if not by_id[item].passed]
        if failed:
            raise RuntimeError(f"Methods failed numerical validation: {', '.join(failed)}")
        if final_report:
            blocked = [item for item in requested if not by_id[item].final_report_eligible]
            if blocked:
                raise PermissionError(
                    "Methods are blocked for final engineering reports: " + ", ".join(blocked)
                )
        return report

    def write_evidence(self, path: Path | str) -> PetrophysicalValidationReport:
        report = self.run_gate()
        destination = Path(path)
        if not destination.is_absolute():
            destination = self.root / destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(destination)
        return report

    def _validate_case(self, method: Mapping[str, Any], case: Mapping[str, Any]) -> MethodValidationResult:
        validation = method["validation"]
        abs_tol = float(validation["absolute_tolerance"])
        rel_tol = float(validation["relative_tolerance"])
        actual = self._execute(str(method["method_id"]), case)
        expected = case["expected"]
        mismatches = tuple(self._compare(expected, actual, abs_tol, rel_tol))
        report_policy = str(method["report_policy"])
        return MethodValidationResult(
            method_id=str(method["method_id"]),
            case_id=str(case["case_id"]),
            passed=not mismatches,
            report_policy=report_policy,
            final_report_eligible=report_policy != "blocked_final_report",
            absolute_tolerance=abs_tol,
            relative_tolerance=rel_tol,
            mismatches=mismatches,
        )

    @staticmethod
    def _series(values: Sequence[Any]) -> pd.Series:
        return pd.Series(list(values), dtype="float64")

    def _execute(self, method_id: str, case: Mapping[str, Any]) -> dict[str, Any]:
        inputs = case.get("inputs", {})
        parameters = dict(case.get("parameters", {}))
        if method_id.startswith("petrophysics.vsh_gr_"):
            result = calculate_shale_volume(self._series(inputs["gr"]), ShaleVolumeParameters(**parameters))
            return {"values": self._values(result)}
        if method_id == "petrophysics.phie_shale_correction":
            result = calculate_effective_porosity(
                self._series(inputs["total_porosity"]), self._series(inputs["shale_volume"])
            )
            return {"values": self._values(result)}
        if method_id == "petrophysics.sw_archie":
            result = calculate_archie_water_saturation(
                self._series(inputs["phie"]), self._series(inputs["rt"]), ArchieParameters(**parameters)
            )
            return {"values": self._values(result)}
        if method_id == "petrophysics.sw_simandoux":
            result = calculate_simandoux_water_saturation(
                self._series(inputs["phie"]), self._series(inputs["rt"]), self._series(inputs["vsh"]), ShalySandParameters(**parameters)
            )
            return {"values": self._values(result)}
        if method_id == "petrophysics.sw_indonesia":
            result = calculate_indonesia_water_saturation(
                self._series(inputs["phie"]), self._series(inputs["rt"]), self._series(inputs["vsh"]), ShalySandParameters(**parameters)
            )
            return {"values": self._values(result)}
        if method_id == "petrophysics.sw_dual_water_foundation":
            result = calculate_dual_water_saturation(
                self._series(inputs["phie"]), self._series(inputs["rt"]), self._series(inputs["vsh"]), DualWaterParameters(**parameters)
            )
            return {"values": self._values(result)}
        if method_id == "petrophysics.net_pay_cutoff_flags":
            reservoir, net, pay = calculate_net_pay_flags(
                vsh=self._series(inputs["vsh"]),
                phie=self._series(inputs["phie"]),
                sw=self._series(inputs["sw"]),
                rt=self._series(inputs["rt"]),
                cutoffs=PetrophysicalCutoffSet(**parameters),
            )
            return {
                "reservoir": [int(value) for value in reservoir],
                "net": [int(value) for value in net],
                "pay": [int(value) for value in pay],
            }
        raise KeyError(f"No production executor registered for petrophysical method: {method_id}")

    @staticmethod
    def _values(series: pd.Series) -> list[float | None]:
        values: list[float | None] = []
        for value in series.tolist():
            if pd.isna(value):
                values.append(None)
            else:
                values.append(float(value))
        return values

    def _compare(
        self,
        expected: Any,
        actual: Any,
        abs_tol: float,
        rel_tol: float,
        path: str = "$",
    ):
        if isinstance(expected, Mapping):
            if not isinstance(actual, Mapping):
                yield ValidationMismatch(path, expected, actual)
                return
            for key in expected:
                if key not in actual:
                    yield ValidationMismatch(f"{path}.{key}", expected[key], "<missing>")
                else:
                    yield from self._compare(expected[key], actual[key], abs_tol, rel_tol, f"{path}.{key}")
            return
        if isinstance(expected, list):
            if not isinstance(actual, list) or len(actual) != len(expected):
                yield ValidationMismatch(path, expected, actual)
                return
            for index, (left, right) in enumerate(zip(expected, actual)):
                yield from self._compare(left, right, abs_tol, rel_tol, f"{path}[{index}]")
            return
        if expected is None or actual is None:
            if expected != actual:
                yield ValidationMismatch(path, expected, actual)
            return
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            expected_float = float(expected)
            actual_float = float(actual)
            tolerance = max(abs_tol, rel_tol * abs(expected_float))
            if not math.isclose(actual_float, expected_float, abs_tol=abs_tol, rel_tol=rel_tol):
                yield ValidationMismatch(
                    path,
                    expected_float,
                    actual_float,
                    absolute_error=abs(actual_float - expected_float),
                    tolerance=tolerance,
                )
            return
        if expected != actual:
            yield ValidationMismatch(path, expected, actual)
