"""Machine-readable petrophysical method and validation contracts.

The module intentionally contains no calculation formulas beyond the short
registry descriptions. Production calculations remain in ``las_editor``;
validation services execute those public functions against static synthetic
reference cases.
"""

from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

PETROPHYSICAL_METHOD_REGISTRY_SCHEMA = "gas-ratio-pro/petrophysical-method-registry/v1"
PETROPHYSICAL_VALIDATION_DATASET_SCHEMA = "gas-ratio-pro/petrophysical-validation-dataset/v1"
PETROPHYSICAL_VALIDATION_GATE_SCHEMA = "gas-ratio-pro/petrophysical-validation-gate/v1"

_DEFAULT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_REGISTRY = _DEFAULT_ROOT / "config" / "petrophysical_method_registry_v225_9.json"
_DEFAULT_DATASET = _DEFAULT_ROOT / "data" / "validation" / "petrophysics" / "petrophysical_validation_cases_v225_9.json"

_REQUIRED_METHOD_FIELDS = {
    "method_id",
    "name",
    "category",
    "implementation",
    "formula",
    "status",
    "report_policy",
    "provenance",
    "inputs",
    "parameters",
    "output",
    "applicability",
    "limitations",
    "validation",
}
_REQUIRED_PROVENANCE_FIELDS = {
    "source_id",
    "title",
    "authors",
    "year",
    "source_type",
    "legal_status",
    "citation_note",
}
_REQUIRED_VALIDATION_FIELDS = {
    "dataset_ids",
    "absolute_tolerance",
    "relative_tolerance",
    "uncertainty",
}
_ALLOWED_REPORT_POLICIES = {"allowed", "allowed_with_warning", "blocked_final_report"}
_ALLOWED_UNITS = {"1", "fraction", "gAPI", "ohm.m", "binary_flag"}


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def contract_fingerprint(*payloads: Mapping[str, Any]) -> str:
    digest = sha256()
    for payload in payloads:
        digest.update(_canonical_bytes(payload))
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Validation contract must be a JSON object: {path}")
    return payload


@lru_cache(maxsize=8)
def load_petrophysical_method_registry(path: str | Path | None = None) -> dict[str, Any]:
    resolved = Path(path).resolve() if path is not None else _DEFAULT_REGISTRY.resolve()
    payload = _load_json(resolved)
    if payload.get("schema") != PETROPHYSICAL_METHOD_REGISTRY_SCHEMA:
        raise ValueError(f"Unsupported petrophysical method registry schema: {payload.get('schema')}")
    return payload


@lru_cache(maxsize=8)
def load_petrophysical_validation_dataset(path: str | Path | None = None) -> dict[str, Any]:
    resolved = Path(path).resolve() if path is not None else _DEFAULT_DATASET.resolve()
    payload = _load_json(resolved)
    if payload.get("schema") != PETROPHYSICAL_VALIDATION_DATASET_SCHEMA:
        raise ValueError(f"Unsupported petrophysical validation dataset schema: {payload.get('schema')}")
    return payload


def validate_registry_contract(
    registry: Mapping[str, Any],
    dataset: Mapping[str, Any],
) -> tuple[str, ...]:
    """Return structural contract errors without executing calculations."""

    errors: list[str] = []
    methods = registry.get("methods")
    cases = dataset.get("cases")
    if not isinstance(methods, list) or not methods:
        return ("registry.methods must be a non-empty list",)
    if not isinstance(cases, list) or not cases:
        return ("dataset.cases must be a non-empty list",)

    case_ids: set[str] = set()
    case_method_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, Mapping):
            errors.append("every validation case must be an object")
            continue
        case_id = str(case.get("case_id", "")).strip()
        method_id = str(case.get("method_id", "")).strip()
        if not case_id:
            errors.append("validation case is missing case_id")
        elif case_id in case_ids:
            errors.append(f"duplicate validation case_id: {case_id}")
        case_ids.add(case_id)
        if not method_id:
            errors.append(f"validation case {case_id or '<unknown>'} is missing method_id")
        case_method_ids.add(method_id)

    method_ids: set[str] = set()
    for method in methods:
        if not isinstance(method, Mapping):
            errors.append("every registry method must be an object")
            continue
        missing = sorted(_REQUIRED_METHOD_FIELDS - set(method))
        method_id = str(method.get("method_id", "")).strip()
        if missing:
            errors.append(f"method {method_id or '<unknown>'} missing fields: {', '.join(missing)}")
        if not method_id:
            errors.append("registry method is missing method_id")
        elif method_id in method_ids:
            errors.append(f"duplicate method_id: {method_id}")
        method_ids.add(method_id)

        provenance = method.get("provenance")
        if not isinstance(provenance, Mapping):
            errors.append(f"method {method_id} provenance must be an object")
        else:
            missing_provenance = sorted(_REQUIRED_PROVENANCE_FIELDS - set(provenance))
            if missing_provenance:
                errors.append(f"method {method_id} provenance missing: {', '.join(missing_provenance)}")
            if not provenance.get("authors"):
                errors.append(f"method {method_id} provenance authors must not be empty")

        if method.get("report_policy") not in _ALLOWED_REPORT_POLICIES:
            errors.append(f"method {method_id} has invalid report_policy")

        validation = method.get("validation")
        if not isinstance(validation, Mapping):
            errors.append(f"method {method_id} validation must be an object")
        else:
            missing_validation = sorted(_REQUIRED_VALIDATION_FIELDS - set(validation))
            if missing_validation:
                errors.append(f"method {method_id} validation missing: {', '.join(missing_validation)}")
            for dataset_id in validation.get("dataset_ids", []):
                if dataset_id not in case_ids:
                    errors.append(f"method {method_id} references missing dataset: {dataset_id}")
            for tolerance_name in ("absolute_tolerance", "relative_tolerance"):
                try:
                    if float(validation.get(tolerance_name, -1)) < 0:
                        raise ValueError
                except (TypeError, ValueError):
                    errors.append(f"method {method_id} has invalid {tolerance_name}")
            uncertainty = validation.get("uncertainty")
            if not isinstance(uncertainty, Mapping) or not uncertainty.get("kind") or not uncertainty.get("note"):
                errors.append(f"method {method_id} requires uncertainty kind and note")

        units = [item.get("unit") for item in method.get("inputs", []) if isinstance(item, Mapping)]
        units += [item.get("unit") for item in method.get("parameters", []) if isinstance(item, Mapping)]
        output = method.get("output")
        if isinstance(output, Mapping):
            units.append(output.get("unit"))
        for unit in units:
            if unit not in _ALLOWED_UNITS:
                errors.append(f"method {method_id} uses unsupported unit: {unit}")

    methods_by_id = {str(item.get("method_id", "")): item for item in methods if isinstance(item, Mapping)}
    for case in cases:
        if not isinstance(case, Mapping):
            continue
        method = methods_by_id.get(str(case.get("method_id", "")))
        if not method:
            continue
        registered_inputs = {str(item.get("name", "")).strip().lower(): item.get("unit") for item in method.get("inputs", []) if isinstance(item, Mapping)}
        case_units = case.get("input_units")
        if not isinstance(case_units, Mapping):
            errors.append(f"validation case {case.get('case_id')} requires input_units")
        else:
            normalized_case_units = {str(name).strip().lower(): unit for name, unit in case_units.items()}
            if normalized_case_units != registered_inputs:
                errors.append(f"validation case {case.get('case_id')} input units do not match registry contract")
        output = method.get("output")
        expected_output_unit = output.get("unit") if isinstance(output, Mapping) else None
        if case.get("output_unit") != expected_output_unit:
            errors.append(f"validation case {case.get('case_id')} output unit does not match registry contract")

    unknown_case_methods = sorted(case_method_ids - method_ids)
    if unknown_case_methods:
        errors.append(f"dataset references unknown methods: {', '.join(unknown_case_methods)}")
    untested_methods = sorted(method_ids - case_method_ids)
    if untested_methods:
        errors.append(f"registry methods without validation cases: {', '.join(untested_methods)}")

    return tuple(errors)


def method_records(
    method_ids: Iterable[str] | None = None,
    *,
    registry_path: str | Path | None = None,
) -> tuple[dict[str, Any], ...]:
    registry = load_petrophysical_method_registry(registry_path)
    methods = tuple(dict(item) for item in registry["methods"])
    if method_ids is None:
        return methods
    wanted = tuple(str(item) for item in method_ids)
    by_id = {str(item["method_id"]): item for item in methods}
    missing = [item for item in wanted if item not in by_id]
    if missing:
        raise KeyError(f"Petrophysical methods are not registered: {', '.join(missing)}")
    return tuple(dict(by_id[item]) for item in wanted)


def method_record(method_id: str, *, registry_path: str | Path | None = None) -> dict[str, Any]:
    return method_records((method_id,), registry_path=registry_path)[0]


def manifest_method_rows(method_ids: Iterable[str]) -> list[dict[str, Any]]:
    """Return compact provenance rows suitable for calculation manifests."""

    rows: list[dict[str, Any]] = []
    for method in method_records(method_ids):
        provenance = method["provenance"]
        validation = method["validation"]
        rows.append(
            {
                "method_id": method["method_id"],
                "name": method["name"],
                "status": method["status"],
                "report_policy": method["report_policy"],
                "implementation": method["implementation"],
                "source_id": provenance["source_id"],
                "source_title": provenance["title"],
                "authors": list(provenance["authors"]),
                "year": provenance["year"],
                "output_unit": method["output"]["unit"],
                "dataset_ids": list(validation["dataset_ids"]),
                "absolute_tolerance": validation["absolute_tolerance"],
                "relative_tolerance": validation["relative_tolerance"],
            }
        )
    return rows


def validation_contract_summary(method_ids: Iterable[str]) -> dict[str, Any]:
    registry = load_petrophysical_method_registry()
    dataset = load_petrophysical_validation_dataset()
    selected = method_records(method_ids)
    return {
        "schema": PETROPHYSICAL_VALIDATION_GATE_SCHEMA,
        "registry_version": registry["version"],
        "dataset_version": dataset["version"],
        "contract_fingerprint": contract_fingerprint(registry, dataset),
        "method_ids": [item["method_id"] for item in selected],
        "gate_required": True,
        "formula_changes_require_validation_evidence": True,
    }
