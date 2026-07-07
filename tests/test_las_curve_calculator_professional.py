import pandas as pd

from las_editor.curve_calculator import (
    apply_curve_calculation,
    build_curve_calculation_manifest,
    build_curve_calculation_plan,
    build_curve_calculation_plan_from_template,
    builtin_curve_formula_templates,
    calculated_curve_spec,
    curve_calculation_issue_table_rows,
    curve_calculation_template_table_rows,
    preview_curve_calculation,
)


def _mud_gas_df() -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "DEPT": [1000.0, 1000.5, 1001.0],
            "C1": [100.0, 120.0, 80.0],
            "C2": [10.0, 15.0, 8.0],
            "C3": [5.0, 6.0, 4.0],
            "C4": [2.0, 3.0, 1.0],
            "C5": [1.0, 1.5, 0.5],
            "POR": [0.12, 0.18, 0.21],
            "FACIES": [0, 1, 0],
        }
    )
    df.attrs["las_units"] = {"DEPT": "M", "C1": "PPM"}
    return df


def test_build_plan_validates_expression_and_used_curves():
    df = _mud_gas_df()
    plan = build_curve_calculation_plan(df, output_curve="por_pct", expression="POR * 100", unit="%")

    assert plan.output_curve == "POR_PCT"
    assert plan.unit == "%"
    assert plan.used_curves == ("POR",)
    assert plan.issues == ()


def test_apply_curve_calculation_adds_working_copy_curve_and_metadata():
    df = _mud_gas_df()
    plan = build_curve_calculation_plan(df, output_curve="PORP", expression="POR * 100", unit="PCT", description="Porosity percent")
    result = apply_curve_calculation(df, plan)

    assert "PORP" in result.data.columns
    assert result.data["PORP"].tolist() == [12.0, 18.0, 21.0]
    assert "PORP" not in df.columns
    assert result.data.attrs["las_units"]["PORP"] == "PCT"
    assert result.history[-1].action == "calculate_curve"
    assert result.diagnostics


def test_builtin_haworth_wetness_template_calculates_ratio():
    df = _mud_gas_df()
    plan = build_curve_calculation_plan_from_template(df, "wetness_haworth")
    result = apply_curve_calculation(df, plan)

    assert "WH" in result.data.columns
    assert round(result.data["WH"].iloc[0], 3) == round(((10 + 5 + 2 + 1) / (100 + 10 + 5 + 2 + 1)) * 100, 3)


def test_if_function_supports_discrete_net_gross_formula():
    df = _mud_gas_df()
    plan = build_curve_calculation_plan_from_template(df, "net_gross_from_facies")
    result = apply_curve_calculation(df, plan)

    assert result.data["NG"].tolist() == [1, 0, 1]


def test_unknown_curve_returns_error_without_mutating_data():
    df = _mud_gas_df()
    plan = build_curve_calculation_plan(df, output_curve="BAD", expression="MISSING + 1")
    result = apply_curve_calculation(df, plan)

    assert "BAD" not in result.data.columns
    assert any(issue.code == "invalid_expression" for issue in result.issues)
    assert result.warnings


def test_existing_curve_requires_overwrite_flag():
    df = _mud_gas_df()
    plan = build_curve_calculation_plan(df, output_curve="POR", expression="POR * 100")

    assert any(issue.code == "curve_exists" for issue in plan.issues)


def test_preview_manifest_tables_and_spec_are_ui_ready():
    df = _mud_gas_df()
    templates = builtin_curve_formula_templates()
    assert any(template.key == "pixler_c1_c2" for template in templates)

    plan = build_curve_calculation_plan(df, output_curve="C1C2", expression="C1 / C2", unit="RATIO")
    preview = preview_curve_calculation(df, plan, max_rows=2)
    result = apply_curve_calculation(df, plan)
    manifest = build_curve_calculation_manifest(result)
    spec = calculated_curve_spec(plan)

    assert len(preview) == 2
    assert preview[0]["C1C2"] == 10.0
    assert manifest["schema"] == "gas-ratio-pro/las-curve-calculator/v1"
    assert manifest["output_curve"] == "C1C2"
    assert spec.mnemonic == "C1C2"
    assert curve_calculation_template_table_rows()
    assert curve_calculation_issue_table_rows(result.issues) == ()
