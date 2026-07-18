from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from core.operator_calibration_package_contract import (
    PACKAGE_DATASET_NAME,
    PACKAGE_MANIFEST_NAME,
    PACKAGE_REGISTRY_NAME,
    build_operator_package_manifest,
    canonical_json_bytes,
)
from core.petrophysical_validation_contract import contract_fingerprint, load_petrophysical_method_registry


def build_operator_package_bytes(
    root: Path,
    *,
    project_id: str,
    package_id: str = "operator-clastic-calibration",
    version: str = "1.0.0",
    final_report_use_allowed: bool = True,
    observed_shift: float = 0.0,
    manifest_mutator=None,
) -> bytes:
    registry = json.loads((root / "config/petrophysical_field_calibration_registry_v225_10.json").read_text(encoding="utf-8"))
    dataset = json.loads((root / "data/validation/petrophysics/petrophysical_field_calibration_cases_v225_10.json").read_text(encoding="utf-8"))
    registry = deepcopy(registry)
    dataset = deepcopy(dataset)
    registry["version"] = version
    registry["description"] = "Operator-owned calibration policies; production formulas are unchanged."
    dataset["version"] = version
    dataset["data_rights"] = "Operator-owned local calibration package for test project."
    calibration_id = f"{package_id}-{version}"
    for item in dataset["calibration_sets"]:
        item["calibration_id"] = calibration_id
        item["owner"] = "Example Operator"
        item["legal_status"] = "operator_owned"
        item["license_id"] = "OPERATOR-INTERNAL"
        item["redistribution_allowed"] = False
        item["source_type"] = "operator_calibration"
        item["source_note"] = "Operator-owned calibration values cleared for local project processing."
    for case in dataset["cases"]:
        case["calibration_id"] = calibration_id
    if observed_shift:
        values = dataset["cases"][0]["observed"]["values"]
        dataset["cases"][0]["observed"]["values"] = [float(value) + float(observed_shift) for value in values]

    registry_bytes = canonical_json_bytes(registry)
    dataset_bytes = canonical_json_bytes(dataset)
    method_registry = load_petrophysical_method_registry(root / "config/petrophysical_method_registry_v225_9.json")
    manifest = build_operator_package_manifest(
        package_id=package_id,
        version=version,
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        operator={"name": "Example Operator", "organization_id": "OP-001"},
        project_scope=[project_id],
        rights={
            "owner": "Example Operator",
            "legal_status": "operator_owned",
            "legal_basis": "Internal operator data governance approval OP-001",
            "data_classification": "confidential",
            "processing_allowed": True,
            "derivative_analysis_allowed": True,
            "final_report_use_allowed": bool(final_report_use_allowed),
            "redistribution_allowed": False,
            "expires_at": "",
        },
        method_registry_fingerprint=contract_fingerprint(method_registry),
        registry_bytes=registry_bytes,
        dataset_bytes=dataset_bytes,
        notes="Synthetic operator package used by automated Stage 5.2 tests.",
    )
    if manifest_mutator is not None:
        manifest_mutator(manifest)
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(PACKAGE_MANIFEST_NAME, canonical_json_bytes(manifest))
        archive.writestr(PACKAGE_REGISTRY_NAME, registry_bytes)
        archive.writestr(PACKAGE_DATASET_NAME, dataset_bytes)
    return output.getvalue()
