import pandas as pd

from las_editor.advanced_saturation_models import (
    ADVANCED_SATURATION_SCHEMA,
    AdvancedSaturationPlan,
    DualWaterParameters,
    SaturationInputCurves,
    ShalySandParameters,
    build_advanced_saturation_manifest,
    calculate_dual_water_saturation,
    calculate_indonesia_water_saturation,
    calculate_simandoux_water_saturation,
    compare_saturation_models,
    recommend_saturation_model,
    render_advanced_saturation_markdown_report,
    run_advanced_saturation_models,
    saturation_comparison_table_rows,
    saturation_issue_table_rows,
    validate_advanced_saturation_plan,
)


def sample_df():
    return pd.DataFrame(
        {
            "DEPT": [1000.0, 1000.5, 1001.0, 1001.5],
            "PHIE": [0.22, 0.18, 0.12, 0.08],
            "RT": [25.0, 12.0, 5.0, 2.0],
            "VSH": [0.08, 0.22, 0.42, 0.65],
        }
    )


def test_simandoux_indonesia_and_dual_water_are_bounded():
    data = sample_df()
    sim = calculate_simandoux_water_saturation(data["PHIE"], data["RT"], data["VSH"], ShalySandParameters())
    ind = calculate_indonesia_water_saturation(data["PHIE"], data["RT"], data["VSH"], ShalySandParameters())
    dual = calculate_dual_water_saturation(data["PHIE"], data["RT"], data["VSH"], DualWaterParameters())
    assert sim.between(0, 1).all()
    assert ind.dropna().between(0, 1).all()
    assert dual.between(0, 1).all()


def test_run_advanced_saturation_models_adds_outputs_and_comparison():
    result = run_advanced_saturation_models(
        sample_df(),
        intervals=[{"name": "Reservoir A", "top": 1000.0, "base": 1001.0}],
        source_references=("docs/sources/application-of-mud-gas-analysis-for-reservoir-evaluation.pdf",),
    )
    assert result.schema == ADVANCED_SATURATION_SCHEMA
    assert not result.issues
    for curve in ["SW_ARCHIE", "SW_SIMANDOUX", "SW_INDONESIA", "SW_DUAL_WATER", "SW_MODEL_SPREAD"]:
        assert curve in result.data.columns
    assert result.comparisons[0].name == "Reservoir A"
    assert result.comparisons[0].sample_count == 3


def test_validate_reports_missing_input_curve():
    issues = validate_advanced_saturation_plan(pd.DataFrame({"PHIE": [0.2]}), AdvancedSaturationPlan())
    assert any(issue.code == "missing_required_curve" for issue in issues)
    assert saturation_issue_table_rows(issues)


def test_recommendation_changes_with_shale_volume_and_spread():
    assert recommend_saturation_model(0.05, 0.05)[0] == "archie"
    assert recommend_saturation_model(0.30, 0.05)[0] == "indonesia"
    assert recommend_saturation_model(0.70, 0.40)[0] == "dual_water_review"
    assert recommend_saturation_model(0.70, 0.40)[1] == "low"


def test_manifest_report_and_table_rows_are_rendered():
    result = run_advanced_saturation_models(sample_df())
    manifest = build_advanced_saturation_manifest(result)
    report = render_advanced_saturation_markdown_report(result)
    rows = saturation_comparison_table_rows(result.comparisons)
    assert manifest["schema"].endswith("/v1")
    assert "Advanced Saturation Models Report" in report
    assert rows and rows[0]["recommended_model"] in {"archie", "indonesia", "dual_water_review"}


def test_custom_curve_mapping_and_prefix():
    data = sample_df().rename(columns={"PHIE": "EFFECTIVE_POR", "RT": "RDEEP"})
    plan = AdvancedSaturationPlan(
        input_curves=SaturationInputCurves(effective_porosity_curve="EFFECTIVE_POR", resistivity_curve="RDEEP", shale_volume_curve="VSH"),
        output_prefix="ADV_",
    )
    result = run_advanced_saturation_models(data, plan=plan)
    assert not result.issues
    assert "ADV_SW_ARCHIE" in result.data.columns


def test_compare_saturation_models_without_depth_uses_full_table():
    result = run_advanced_saturation_models(sample_df().drop(columns=["DEPT"]))
    comparisons = compare_saturation_models(result.data, plan=result.plan)
    assert comparisons[0].name == "Full table"
    assert comparisons[0].sample_count == 4
