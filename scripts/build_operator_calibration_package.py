#!/usr/bin/env python3
"""Build a Stage 5.2 operator calibration ZIP package.

The command does not alter formulas or calibration values.  It wraps an
existing calibration registry and dataset in the immutable operator package
contract with project scope, data-rights declarations and SHA-256 checksums.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.operator_calibration_package_contract import (  # noqa: E402
    PACKAGE_DATASET_NAME,
    PACKAGE_MANIFEST_NAME,
    PACKAGE_REGISTRY_NAME,
    build_operator_package_manifest,
    canonical_json_bytes,
)
from core.petrophysical_calibration_contract import (  # noqa: E402
    validate_field_calibration_contract,
)
from core.petrophysical_validation_contract import (  # noqa: E402
    contract_fingerprint,
    load_petrophysical_method_registry,
)


def build_archive(
    *,
    registry: dict,
    dataset: dict,
    package_id: str,
    version: str,
    project_ids: tuple[str, ...],
    operator_name: str,
    organization_id: str,
    owner: str,
    legal_status: str,
    legal_basis: str,
    data_classification: str,
    final_report_use_allowed: bool,
    redistribution_allowed: bool,
    expires_at: str = "",
    notes: str = "",
    application_root: Path = ROOT,
) -> bytes:
    method_registry = load_petrophysical_method_registry(
        application_root / "config" / "petrophysical_method_registry_v225_9.json"
    )
    known_ids = {str(item["method_id"]) for item in method_registry.get("methods", [])}
    errors = validate_field_calibration_contract(
        registry,
        dataset,
        known_method_ids=known_ids,
        require_redistribution_allowed=False,
    )
    if errors:
        raise ValueError("Calibration contract is invalid: " + "; ".join(errors))
    registry_bytes = canonical_json_bytes(registry)
    dataset_bytes = canonical_json_bytes(dataset)
    manifest = build_operator_package_manifest(
        package_id=package_id,
        version=version,
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        operator={"name": operator_name, "organization_id": organization_id},
        project_scope=list(project_ids),
        rights={
            "owner": owner,
            "legal_status": legal_status,
            "legal_basis": legal_basis,
            "data_classification": data_classification,
            "processing_allowed": True,
            "derivative_analysis_allowed": True,
            "final_report_use_allowed": bool(final_report_use_allowed),
            "redistribution_allowed": bool(redistribution_allowed),
            "expires_at": str(expires_at),
        },
        method_registry_fingerprint=contract_fingerprint(method_registry),
        registry_bytes=registry_bytes,
        dataset_bytes=dataset_bytes,
        notes=notes,
    )
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(PACKAGE_MANIFEST_NAME, canonical_json_bytes(manifest))
        archive.writestr(PACKAGE_REGISTRY_NAME, registry_bytes)
        archive.writestr(PACKAGE_DATASET_NAME, dataset_bytes)
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--package-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--project-id", action="append", required=True, dest="project_ids")
    parser.add_argument("--operator-name", required=True)
    parser.add_argument("--organization-id", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--legal-status", choices=("operator_owned", "licensed", "public_domain"), required=True)
    parser.add_argument("--legal-basis", required=True)
    parser.add_argument("--data-classification", choices=("public", "internal", "confidential", "restricted"), default="confidential")
    parser.add_argument("--final-report-use-allowed", action="store_true")
    parser.add_argument("--redistribution-allowed", action="store_true")
    parser.add_argument("--expires-at", default="")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    payload = build_archive(
        registry=registry,
        dataset=dataset,
        package_id=args.package_id,
        version=args.version,
        project_ids=tuple(args.project_ids),
        operator_name=args.operator_name,
        organization_id=args.organization_id,
        owner=args.owner,
        legal_status=args.legal_status,
        legal_basis=args.legal_basis,
        data_classification=args.data_classification,
        final_report_use_allowed=args.final_report_use_allowed,
        redistribution_allowed=args.redistribution_allowed,
        expires_at=args.expires_at,
        notes=args.notes,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    print(f"Created {args.output} ({len(payload)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
