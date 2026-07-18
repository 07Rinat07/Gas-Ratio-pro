from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from core.petrophysical_calibration_contract import (
    load_field_calibration_dataset,
    load_field_calibration_registry,
    validate_field_calibration_contract,
)
from core.petrophysical_report_context import petrophysical_method_ids_from_frame
from core.petrophysical_validation_contract import load_petrophysical_method_registry
from las_editor.advanced_saturation_models import AdvancedSaturationPlan, run_advanced_saturation_models
from las_editor.petrophysical_workspace import (
    PetrophysicalInputCurves,
    PetrophysicalPlan,
    run_petrophysical_workspace,
)
from services.petrophysical_calibration_application_service import (
    PetrophysicalCalibrationApplicationService,
)
from services.petrophysical_report_authorization_application_service import (
    PetrophysicalReportAuthorizationApplicationService,
)
from services.petrophysical_validation_diagnostics import build_petrophysical_diagnostics_view
from services.petrophysical_validation_application_service import PetrophysicalValidationApplicationService

ROOT = Path(__file__).resolve().parents[1]


def test_field_calibration_contract_is_legally_cleared_and_covers_all_methods() -> None:
    methods = load_petrophysical_method_registry(ROOT / "config/petrophysical_method_registry_v225_9.json")
    registry = load_field_calibration_registry(ROOT / "config/petrophysical_field_calibration_registry_v225_10.json")
    dataset = load_field_calibration_dataset(ROOT / "data/validation/petrophysics/petrophysical_field_calibration_cases_v225_10.json")
    known = {item["method_id"] for item in methods["methods"]}
    assert validate_field_calibration_contract(registry, dataset, known_method_ids=known) == ()
    assert {item["method_id"] for item in registry["methods"]} == known
    assert all(item["redistribution_allowed"] for item in dataset["calibration_sets"])
    assert all(item["legal_status"] == "project_owned" for item in dataset["calibration_sets"])


def test_calibration_gate_produces_sensitivity_and_uncertainty_envelopes() -> None:
    report = PetrophysicalCalibrationApplicationService(root=ROOT).run_gate()
    assert report.passed
    assert report.calibrated_method_count == 10
    assert report.final_report_calibrated_count == 9
    assert report.gate_id.startswith("cal-")
    by_id = {item.method_id: item for item in report.methods}
    archie = by_id["petrophysics.sw_archie"]
    assert archie.metrics.rmse < archie.acceptance["max_rmse"]
    assert {item.parameter for item in archie.sensitivity} == {"a", "m", "n", "rw"}
    assert archie.uncertainty_envelope.max_width > 0
    phie = by_id["petrophysics.phie_shale_correction"]
    assert phie.sensitivity == ()
    assert phie.uncertainty_envelope.max_width == 0
    dual = by_id["petrophysics.sw_dual_water_foundation"]
    assert dual.passed and not dual.final_report_calibrated


def test_uncleared_calibration_dataset_is_rejected(tmp_path: Path) -> None:
    source = json.loads((ROOT / "data/validation/petrophysics/petrophysical_field_calibration_cases_v225_10.json").read_text())
    source["calibration_sets"][0]["redistribution_allowed"] = False
    target = tmp_path / "dataset.json"
    target.write_text(json.dumps(source), encoding="utf-8")
    report = PetrophysicalCalibrationApplicationService(root=ROOT, dataset_path=target).run_gate()
    assert not report.passed
    assert any("not cleared" in item or "uncleared" in item for item in report.structural_errors)


def test_final_report_authorization_allows_calibrated_methods_and_blocks_foundation_dual_water() -> None:
    service = PetrophysicalReportAuthorizationApplicationService(root=ROOT)
    allowed = service.authorize(("petrophysics.sw_archie", "petrophysics.net_pay_cutoff_flags"))
    assert allowed.passed
    allowed.assert_authorized()
    assert allowed.authorization_id.startswith("auth-")
    blocked = service.authorize(("petrophysics.sw_dual_water_foundation",))
    assert not blocked.passed
    assert blocked.methods[0].reasons == ("report_policy_blocked",)
    with pytest.raises(PermissionError):
        blocked.assert_authorized()


def test_diagnostics_are_localized_for_all_supported_languages() -> None:
    validation = PetrophysicalValidationApplicationService(root=ROOT).run_gate()
    calibration = PetrophysicalCalibrationApplicationService(root=ROOT).run_gate()
    for locale, expected in (("ru", "Петрофизический"), ("kk", "Петрофизикалық"), ("en", "Petrophysical")):
        view = build_petrophysical_diagnostics_view(validation, calibration, locale=locale)
        assert expected in view.title
        assert len(view.rows) == 10
        assert view.validation_passed and view.calibration_passed
        assert view.labels["method"]
        assert view.disclaimer


def test_calculation_frames_carry_machine_readable_method_context() -> None:
    source = pd.DataFrame({
        "DEPTH": [1000.0, 1000.5, 1001.0],
        "GR": [40.0, 65.0, 90.0],
        "POR": [0.22, 0.18, 0.15],
        "RT": [12.0, 7.0, 4.0],
    })
    result = run_petrophysical_workspace(
        source,
        plan=PetrophysicalPlan(input_curves=PetrophysicalInputCurves(depth_curve="DEPTH", gamma_ray_curve="GR", porosity_curve="POR", resistivity_curve="RT")),
    )
    method_ids = petrophysical_method_ids_from_frame(result.data)
    assert method_ids == (
        "petrophysics.vsh_gr_linear",
        "petrophysics.phie_shale_correction",
        "petrophysics.sw_archie",
        "petrophysics.net_pay_cutoff_flags",
    )
    advanced = run_advanced_saturation_models(result.data, plan=AdvancedSaturationPlan(overwrite=True))
    advanced_ids = petrophysical_method_ids_from_frame(advanced.data)
    assert set(method_ids).issubset(advanced_ids)
    assert "petrophysics.sw_dual_water_foundation" in advanced_ids
