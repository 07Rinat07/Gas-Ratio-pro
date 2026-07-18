from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.application_service_container import ApplicationServiceContainer
from core.petrophysical_validation_contract import (
    contract_fingerprint,
    load_petrophysical_method_registry,
    load_petrophysical_validation_dataset,
    manifest_method_rows,
    method_record,
    validate_registry_contract,
)
from core.runtime_service_registry import RuntimeServiceRegistry
from las_editor.advanced_saturation_models import build_advanced_saturation_manifest, run_advanced_saturation_models
from las_editor.petrophysical_workspace import build_petrophysical_manifest, run_petrophysical_workspace
from services.petrophysical_validation_application_service import PetrophysicalValidationApplicationService

ROOT = Path(__file__).resolve().parents[1]


def test_registry_and_reference_dataset_form_one_valid_contract() -> None:
    registry = load_petrophysical_method_registry()
    dataset = load_petrophysical_validation_dataset()
    assert registry["version"] == "v225.9"
    assert dataset["version"] == "v225.9"
    assert len(registry["methods"]) == 10
    assert len(dataset["cases"]) == 10
    assert validate_registry_contract(registry, dataset) == ()
    assert contract_fingerprint(registry, dataset) == contract_fingerprint(registry, dataset)


def test_each_method_has_provenance_units_tolerance_and_uncertainty() -> None:
    registry = load_petrophysical_method_registry()
    for method in registry["methods"]:
        assert method["provenance"]["source_id"]
        assert method["provenance"]["authors"]
        assert method["inputs"]
        assert method["output"]["unit"]
        assert method["validation"]["dataset_ids"]
        assert method["validation"]["absolute_tolerance"] >= 0
        assert method["validation"]["relative_tolerance"] >= 0
        assert method["validation"]["uncertainty"]["kind"]
        assert method["validation"]["uncertainty"]["note"]


def test_validation_gate_executes_all_production_methods() -> None:
    report = PetrophysicalValidationApplicationService(root=ROOT).run_gate()
    assert report.passed is True
    assert report.validated_method_count == 10
    assert report.final_report_eligible_count == 9
    assert all(item.passed for item in report.methods)
    assert report.gate_id.startswith("petro-")


def test_foundation_dual_water_is_reproducible_but_blocked_for_final_report() -> None:
    service = PetrophysicalValidationApplicationService(root=ROOT)
    report = service.authorize_methods(("petrophysics.sw_dual_water_foundation",))
    result = next(item for item in report.methods if item.method_id == "petrophysics.sw_dual_water_foundation")
    assert result.passed is True
    assert result.report_policy == "blocked_final_report"
    with pytest.raises(PermissionError):
        service.authorize_methods(("petrophysics.sw_dual_water_foundation",), final_report=True)


def test_archie_is_authorized_for_final_report_with_warning_policy() -> None:
    service = PetrophysicalValidationApplicationService(root=ROOT)
    report = service.authorize_methods(("petrophysics.sw_archie",), final_report=True)
    result = next(item for item in report.methods if item.method_id == "petrophysics.sw_archie")
    assert result.final_report_eligible is True


def test_tampered_reference_value_fails_gate(tmp_path: Path) -> None:
    dataset = load_petrophysical_validation_dataset()
    tampered = json.loads(json.dumps(dataset))
    tampered["cases"][0]["expected"]["values"][1] = 0.99
    dataset_path = tmp_path / "cases.json"
    dataset_path.write_text(json.dumps(tampered), encoding="utf-8")
    report = PetrophysicalValidationApplicationService(
        root=ROOT,
        dataset_path=dataset_path,
    ).run_gate()
    assert report.passed is False
    failed = [item for item in report.methods if not item.passed]
    assert [item.method_id for item in failed] == ["petrophysics.vsh_gr_linear"]
    assert failed[0].mismatches[0].path == "$.values[1]"


def test_unit_contract_mismatch_is_rejected_before_execution(tmp_path: Path) -> None:
    dataset = load_petrophysical_validation_dataset()
    tampered = json.loads(json.dumps(dataset))
    tampered["cases"][5]["input_units"]["rt"] = "m"
    dataset_path = tmp_path / "cases.json"
    dataset_path.write_text(json.dumps(tampered), encoding="utf-8")
    report = PetrophysicalValidationApplicationService(root=ROOT, dataset_path=dataset_path).run_gate()
    assert report.passed is False
    assert any("input units" in item for item in report.structural_errors)
    assert report.methods == ()


def test_evidence_is_written_atomically(tmp_path: Path) -> None:
    destination = tmp_path / "petro-evidence.json"
    report = PetrophysicalValidationApplicationService(root=ROOT).write_evidence(destination)
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert report.passed is True
    assert payload["gate_id"] == report.gate_id
    assert payload["validated_method_count"] == 10
    assert not destination.with_suffix(".json.tmp").exists()


def test_application_service_container_reuses_validation_boundary() -> None:
    container = ApplicationServiceContainer(RuntimeServiceRegistry(), {})
    first = container.petrophysical_validation(root=ROOT)
    second = container.petrophysical_validation(root=ROOT)
    assert first is second
    assert first.run_gate().passed is True
    assert any(item.service_name == "petrophysical_validation" for item in container.descriptors())


def test_calculation_manifests_embed_method_provenance_and_gate_contract() -> None:
    base_manifest = build_petrophysical_manifest(run_petrophysical_workspace(
        __import__("pandas").DataFrame({"DEPT": [1.0], "GR": [35.0], "POR": [0.2], "RT": [10.0]})
    ))
    assert "petrophysics.sw_archie" in base_manifest["method_ids"]
    assert base_manifest["method_provenance"]
    assert base_manifest["validation_contract"]["gate_required"] is True

    advanced_manifest = build_advanced_saturation_manifest(run_advanced_saturation_models(
        __import__("pandas").DataFrame({"DEPT": [1.0], "PHIE": [0.2], "RT": [10.0], "VSH": [0.0]})
    ))
    by_id = {item["method_id"]: item for item in advanced_manifest["method_provenance"]}
    assert by_id["petrophysics.sw_dual_water_foundation"]["report_policy"] == "blocked_final_report"
    assert advanced_manifest["validation_contract"]["registry_version"] == "v225.9"


def test_registry_lookup_and_manifest_rows_are_stable() -> None:
    archie = method_record("petrophysics.sw_archie")
    rows = manifest_method_rows(("petrophysics.sw_archie",))
    assert archie["provenance"]["source_id"] == "archie.1942"
    assert rows[0]["output_unit"] == "fraction"
    assert rows[0]["dataset_ids"] == ["sw_archie_reference"]
