"""Contracts for Stage 5.1 field calibration and report authorization.

Only project-owned or legally cleared calibration datasets are accepted.  The
contract is deliberately independent from calculation formulas: production
methods are executed through :mod:`core.petrophysical_method_executor`.
"""

from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

FIELD_CALIBRATION_REGISTRY_SCHEMA = "gas-ratio-pro/petrophysical-field-calibration-registry/v1"
FIELD_CALIBRATION_DATASET_SCHEMA = "gas-ratio-pro/petrophysical-field-calibration-dataset/v1"
FIELD_CALIBRATION_GATE_SCHEMA = "gas-ratio-pro/petrophysical-field-calibration-gate/v1"
REPORT_AUTHORIZATION_SCHEMA = "gas-ratio-pro/petrophysical-report-authorization/v1"

_DEFAULT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_REGISTRY = _DEFAULT_ROOT / "config" / "petrophysical_field_calibration_registry_v225_10.json"
_DEFAULT_DATASET = _DEFAULT_ROOT / "data" / "validation" / "petrophysics" / "petrophysical_field_calibration_cases_v225_10.json"

_ALLOWED_LEGAL_STATUS = {"project_owned", "operator_owned", "licensed", "public_domain"}
_ALLOWED_CALIBRATION_POLICY = {"required_final_report", "diagnostic_only", "not_required"}
_ALLOWED_DISTRIBUTIONS = {"triangular", "uniform", "fixed"}


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Calibration contract must be a JSON object: {path}")
    return payload


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def calibration_contract_fingerprint(*payloads: Mapping[str, Any]) -> str:
    digest = sha256()
    for payload in payloads:
        digest.update(_canonical_bytes(payload))
    return digest.hexdigest()


@lru_cache(maxsize=8)
def load_field_calibration_registry(path: str | Path | None = None) -> dict[str, Any]:
    resolved = Path(path).resolve() if path is not None else _DEFAULT_REGISTRY.resolve()
    payload = _load(resolved)
    if payload.get("schema") != FIELD_CALIBRATION_REGISTRY_SCHEMA:
        raise ValueError(f"Unsupported calibration registry schema: {payload.get('schema')}")
    return payload


@lru_cache(maxsize=8)
def load_field_calibration_dataset(path: str | Path | None = None) -> dict[str, Any]:
    resolved = Path(path).resolve() if path is not None else _DEFAULT_DATASET.resolve()
    payload = _load(resolved)
    if payload.get("schema") != FIELD_CALIBRATION_DATASET_SCHEMA:
        raise ValueError(f"Unsupported calibration dataset schema: {payload.get('schema')}")
    return payload


def validate_field_calibration_contract(
    registry: Mapping[str, Any],
    dataset: Mapping[str, Any],
    *,
    known_method_ids: set[str] | None = None,
    require_redistribution_allowed: bool = True,
) -> tuple[str, ...]:
    errors: list[str] = []
    methods = registry.get("methods")
    calibration_sets = dataset.get("calibration_sets")
    cases = dataset.get("cases")
    if not isinstance(methods, list) or not methods:
        return ("calibration registry methods must be a non-empty list",)
    if not isinstance(calibration_sets, list) or not calibration_sets:
        errors.append("calibration dataset calibration_sets must be a non-empty list")
        calibration_sets = []
    if not isinstance(cases, list) or not cases:
        errors.append("calibration dataset cases must be a non-empty list")
        cases = []

    set_ids: set[str] = set()
    cleared_set_ids: set[str] = set()
    for record in calibration_sets:
        if not isinstance(record, Mapping):
            errors.append("every calibration set must be an object")
            continue
        set_id = str(record.get("calibration_id", "")).strip()
        if not set_id:
            errors.append("calibration set missing calibration_id")
            continue
        if set_id in set_ids:
            errors.append(f"duplicate calibration_id: {set_id}")
        set_ids.add(set_id)
        legal_status = str(record.get("legal_status", "")).strip()
        if legal_status not in _ALLOWED_LEGAL_STATUS:
            errors.append(f"calibration set {set_id} has unsupported legal_status: {legal_status}")
        if not str(record.get("owner", "")).strip():
            errors.append(f"calibration set {set_id} requires owner")
        if not str(record.get("source_note", "")).strip():
            errors.append(f"calibration set {set_id} requires source_note")
        redistribution_allowed = bool(record.get("redistribution_allowed", False))
        if require_redistribution_allowed and not redistribution_allowed:
            errors.append(f"calibration set {set_id} is not cleared for release distribution")
        if legal_status in _ALLOWED_LEGAL_STATUS and (redistribution_allowed or not require_redistribution_allowed):
            cleared_set_ids.add(set_id)

    case_ids: set[str] = set()
    case_by_id: dict[str, Mapping[str, Any]] = {}
    for case in cases:
        if not isinstance(case, Mapping):
            errors.append("every calibration case must be an object")
            continue
        case_id = str(case.get("case_id", "")).strip()
        method_id = str(case.get("method_id", "")).strip()
        set_id = str(case.get("calibration_id", "")).strip()
        if not case_id:
            errors.append("calibration case missing case_id")
            continue
        if case_id in case_ids:
            errors.append(f"duplicate calibration case_id: {case_id}")
        case_ids.add(case_id)
        case_by_id[case_id] = case
        if known_method_ids is not None and method_id not in known_method_ids:
            errors.append(f"calibration case {case_id} references unknown method: {method_id}")
        if set_id not in cleared_set_ids:
            errors.append(f"calibration case {case_id} references uncleared set: {set_id}")
        if not isinstance(case.get("inputs"), Mapping):
            errors.append(f"calibration case {case_id} requires inputs")
        if not isinstance(case.get("parameters"), Mapping):
            errors.append(f"calibration case {case_id} requires parameters")
        if not isinstance(case.get("observed"), Mapping):
            errors.append(f"calibration case {case_id} requires observed values")

    registered_methods: set[str] = set()
    referenced_cases: set[str] = set()
    for record in methods:
        if not isinstance(record, Mapping):
            errors.append("every calibration method record must be an object")
            continue
        method_id = str(record.get("method_id", "")).strip()
        if not method_id:
            errors.append("calibration method record missing method_id")
            continue
        if method_id in registered_methods:
            errors.append(f"duplicate calibration method record: {method_id}")
        registered_methods.add(method_id)
        if known_method_ids is not None and method_id not in known_method_ids:
            errors.append(f"calibration registry references unknown method: {method_id}")
        policy = str(record.get("calibration_policy", "")).strip()
        if policy not in _ALLOWED_CALIBRATION_POLICY:
            errors.append(f"method {method_id} has invalid calibration_policy")
        method_case_ids = record.get("case_ids")
        if not isinstance(method_case_ids, list) or not method_case_ids:
            errors.append(f"method {method_id} requires case_ids")
            method_case_ids = []
        for case_id in method_case_ids:
            case_id = str(case_id)
            referenced_cases.add(case_id)
            case = case_by_id.get(case_id)
            if case is None:
                errors.append(f"method {method_id} references missing calibration case: {case_id}")
            elif str(case.get("method_id")) != method_id:
                errors.append(f"calibration case {case_id} belongs to another method")
        acceptance = record.get("acceptance")
        if not isinstance(acceptance, Mapping):
            errors.append(f"method {method_id} requires acceptance metrics")
        else:
            for name in ("max_rmse", "max_mae", "max_abs_error", "max_abs_bias"):
                try:
                    if float(acceptance.get(name, -1)) < 0:
                        raise ValueError
                except (TypeError, ValueError):
                    errors.append(f"method {method_id} has invalid {name}")
        distributions = record.get("parameter_distributions", [])
        if not isinstance(distributions, list):
            errors.append(f"method {method_id} parameter_distributions must be a list")
            distributions = []
        names: set[str] = set()
        for distribution in distributions:
            if not isinstance(distribution, Mapping):
                errors.append(f"method {method_id} has invalid parameter distribution")
                continue
            name = str(distribution.get("name", "")).strip()
            if not name or name in names:
                errors.append(f"method {method_id} has missing or duplicate distribution name: {name}")
            names.add(name)
            if distribution.get("distribution") not in _ALLOWED_DISTRIBUTIONS:
                errors.append(f"method {method_id} parameter {name} has unsupported distribution")
            try:
                low = float(distribution["low"])
                mode = float(distribution["mode"])
                high = float(distribution["high"])
                if not low <= mode <= high:
                    raise ValueError
            except (KeyError, TypeError, ValueError):
                errors.append(f"method {method_id} parameter {name} requires low <= mode <= high")

    unreferenced = sorted(case_ids - referenced_cases)
    if unreferenced:
        errors.append("unreferenced calibration cases: " + ", ".join(unreferenced))
    return tuple(errors)


def calibration_records(
    method_ids: tuple[str, ...] | list[str] | None = None,
    *,
    registry_path: str | Path | None = None,
) -> tuple[dict[str, Any], ...]:
    registry = load_field_calibration_registry(registry_path)
    records = tuple(dict(item) for item in registry["methods"])
    if method_ids is None:
        return records
    wanted = tuple(str(item) for item in method_ids)
    by_id = {str(item["method_id"]): item for item in records}
    missing = [item for item in wanted if item not in by_id]
    if missing:
        raise KeyError("Petrophysical methods are not covered by calibration registry: " + ", ".join(missing))
    return tuple(dict(by_id[item]) for item in wanted)


def manifest_calibration_rows(
    method_ids: tuple[str, ...] | list[str],
    *,
    registry_path: str | Path | None = None,
    dataset_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    dataset = load_field_calibration_dataset(dataset_path)
    cases = {str(item["case_id"]): item for item in dataset.get("cases", [])}
    rows: list[dict[str, Any]] = []
    for record in calibration_records(method_ids, registry_path=registry_path):
        case_ids = [str(item) for item in record.get("case_ids", ())]
        calibration_ids = sorted({str(cases[item]["calibration_id"]) for item in case_ids if item in cases})
        rows.append({
            "method_id": str(record["method_id"]),
            "calibration_policy": str(record["calibration_policy"]),
            "case_ids": case_ids,
            "calibration_ids": calibration_ids,
            "sensitivity_strategy": str(record.get("uncertainty", {}).get("strategy", "")),
            "parameter_distributions": [dict(item) for item in record.get("parameter_distributions", ())],
            "acceptance": dict(record.get("acceptance", {})),
        })
    return rows


def field_calibration_contract_summary(
    method_ids: tuple[str, ...] | list[str],
    *,
    registry_path: str | Path | None = None,
    dataset_path: str | Path | None = None,
) -> dict[str, Any]:
    registry = load_field_calibration_registry(registry_path)
    dataset = load_field_calibration_dataset(dataset_path)
    rows = manifest_calibration_rows(
        method_ids,
        registry_path=registry_path,
        dataset_path=dataset_path,
    )
    sets = [
        {
            "calibration_id": str(item.get("calibration_id", "")),
            "owner": str(item.get("owner", "")),
            "legal_status": str(item.get("legal_status", "")),
            "redistribution_allowed": bool(item.get("redistribution_allowed", False)),
        }
        for item in dataset.get("calibration_sets", ())
    ]
    return {
        "schema": FIELD_CALIBRATION_REGISTRY_SCHEMA,
        "registry_version": str(registry.get("version", "")),
        "dataset_version": str(dataset.get("version", "")),
        "contract_fingerprint": calibration_contract_fingerprint(registry, dataset),
        "method_ids": [row["method_id"] for row in rows],
        "calibration_policies": {row["method_id"]: row["calibration_policy"] for row in rows},
        "calibration_sets": sets,
    }
