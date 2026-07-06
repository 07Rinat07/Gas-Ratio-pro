import pandas as pd

from projects.interpretation_workspace import (
    InterpretationCutoffs,
    PetrophysicalParameters,
    export_interpreted_curves_to_dataframe,
    list_interpretation_calculation_runs,
    list_interpretation_presets,
    preview_interpreted_curves,
    run_interpretation_calculation,
    save_interpretation_preset,
    validate_interpretation_inputs,
)
from projects.project_manager import create_project


def test_interpretation_presets_are_saved_and_listed(tmp_path) -> None:
    project = create_project(tmp_path, name="Preset Demo")

    preset = save_interpretation_preset(
        tmp_path,
        project.id,
        "Field A Archie",
        description="Local field parameters",
        parameters=PetrophysicalParameters(rw=0.05),
        cutoffs=InterpretationCutoffs(vsh_max=0.40, phie_min=0.10, sw_max=0.70),
        vsh_method="linear",
        saturation_method="archie",
    )
    presets = list_interpretation_presets(tmp_path, project.id)

    assert preset.id == "field-a-archie"
    assert any(row.id == "clean-sand-archie" for row in presets)
    assert any(row.id == preset.id and row.parameters["rw"] == 0.05 for row in presets)


def test_interpretation_input_validation_reports_missing_and_depth_warnings() -> None:
    frame = pd.DataFrame({"DEPT": [1000.0, 1000.0, 999.5], "GR": [40, 50, 60], "PHIT": [0.2, None, 0.1]})

    validation = validate_interpretation_inputs(frame)

    assert not validation.is_valid
    assert "RT" in validation.missing_required_curves
    assert any("дубликаты" in warning for warning in validation.warnings)
    assert any("PHIT" in warning for warning in validation.warnings)


def test_interpretation_calculation_run_history_preview_and_export(tmp_path) -> None:
    project = create_project(tmp_path, name="Run Demo")
    frame = pd.DataFrame(
        {
            "DEPT": [1000.0, 1000.5, 1001.0],
            "GR": [35, 80, 140],
            "PHIT": [0.24, 0.18, 0.08],
            "RT": [40, 12, 2],
        }
    )
    preset = save_interpretation_preset(tmp_path, project.id, "Shaly Run", saturation_method="simandoux", permeability_method="coates")

    run, interpreted, previews = run_interpretation_calculation(
        tmp_path,
        project.id,
        "Main pass",
        frame,
        preset=preset,
        source_type="las",
        source_id="well-a.las",
        well_id="well-a",
    )
    history = list_interpretation_calculation_runs(tmp_path, project.id)
    export_frame = export_interpreted_curves_to_dataframe(frame, interpreted, curves=("VSH", "PHIE", "SW"))
    direct_preview = preview_interpreted_curves(interpreted, curves=("VSH", "PHIE"))

    assert run.status == "completed"
    assert run.rows == 3
    assert {"VSH", "PHIE", "SW"}.issubset(interpreted.columns)
    assert {"VSH", "PHIE", "SW"}.issubset(export_frame.columns)
    assert history[-1].name == "Main pass"
    assert any(preview.name == "SW" and preview.points == 3 for preview in previews)
    assert len(direct_preview) == 2
