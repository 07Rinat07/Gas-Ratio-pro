import pandas as pd
import pytest

from projects.formula_builder import (
    calculate_formula_curve,
    detect_formula_dependencies,
    list_formula_templates,
    save_formula_record,
    list_formula_records,
    summarize_formula_builder,
    validate_formula_expression,
    build_formula_dependency_graph,
)
from projects.project_manager import create_project


def test_formula_builder_validates_and_detects_dependencies() -> None:
    result = validate_formula_expression("(GR - GR_MIN) / (GR_MAX - GR_MIN)", {"GR", "GR_MIN", "GR_MAX"})

    assert result.valid is True
    assert result.dependencies == ("GR", "GR_MAX", "GR_MIN")
    assert detect_formula_dependencies("PHIT * (1 - VSH)") == ("PHIT", "VSH")

    bad = validate_formula_expression("__import__('os').system('dir')")
    assert bad.valid is False
    assert bad.errors


def test_formula_builder_calculates_new_curve_with_constants() -> None:
    frame = pd.DataFrame({"GR": [60, 90, 120], "PHIT": [0.25, 0.20, 0.12]})

    result = calculate_formula_curve(frame, "(GR - GR_MIN) / (GR_MAX - GR_MIN)", "VSH", constants={"GR_MIN": 30, "GR_MAX": 150})

    assert "VSH" in result.columns
    assert result["VSH"].round(3).tolist() == [0.25, 0.5, 0.75]
    assert "VSH" not in frame.columns


def test_formula_builder_rejects_missing_variables() -> None:
    frame = pd.DataFrame({"GR": [80]})

    with pytest.raises(ValueError, match="отсутствуют переменные"):
        calculate_formula_curve(frame, "GR / RT", "BAD")


def test_formula_builder_templates_and_project_records(tmp_path) -> None:
    project = create_project(tmp_path, name="Formula Demo")

    templates = list_formula_templates()
    assert any(template.output_curve == "VSH" for template in templates)

    record = save_formula_record(
        tmp_path,
        project.id,
        "VSH custom",
        "(GR - GR_MIN) / (GR_MAX - GR_MIN)",
        "VSH",
        source_type="las",
        source_id="las-1",
        well_id="well-a",
        units="v/v",
        category="petrophysics",
    )

    records = list_formula_records(tmp_path, project.id)
    assert records[0].id == record.id
    assert summarize_formula_builder(tmp_path, project.id).formulas == 1
    assert build_formula_dependency_graph(records) == [
        {"from": "GR", "to": "VSH", "formula": "VSH custom"},
        {"from": "GR_MAX", "to": "VSH", "formula": "VSH custom"},
        {"from": "GR_MIN", "to": "VSH", "formula": "VSH custom"},
    ]
