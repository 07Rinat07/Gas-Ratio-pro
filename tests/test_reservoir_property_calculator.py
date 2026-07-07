import pandas as pd

from las_editor.reservoir_property_calculator import (
    RESERVOIR_PROPERTY_CALCULATOR_SCHEMA,
    ReservoirPropertyInputCurves,
    ReservoirPropertyParameters,
    ReservoirPropertyPlan,
    build_reservoir_property_manifest,
    calculate_bulk_rock_volume,
    calculate_pore_volumes,
    calculate_sample_thickness,
    render_reservoir_property_markdown_report,
    reservoir_property_issue_table_rows,
    reservoir_volume_table_rows,
    run_reservoir_property_calculator,
    summarize_reservoir_volume_intervals,
    validate_reservoir_property_plan,
)


def sample_df():
    return pd.DataFrame(
        {
            "DEPT": [1000.0, 1000.5, 1001.0, 1001.5],
            "PHIE": [0.20, 0.18, 0.12, 0.05],
            "SW_ARCHIE": [0.30, 0.40, 0.70, 0.90],
            "NG": [1.0, 0.8, 0.5, 0.0],
            "PAY": [1, 1, 0, 0],
        }
    )


def test_sample_thickness_uses_median_for_last_sample():
    thickness = calculate_sample_thickness(pd.Series([1000.0, 1000.5, 1001.0]))
    assert list(thickness) == [0.5, 0.5, 0.5]


def test_bulk_rock_volume_uses_depth_step_and_area():
    brv = calculate_bulk_rock_volume(pd.Series([1.0, 2.0, 3.0]), 100.0)
    assert list(brv) == [100.0, 100.0, 100.0]


def test_pore_volumes_are_calculated_and_clamped():
    nrv, pv, hcpv = calculate_pore_volumes(
        pd.Series([100.0, 100.0]),
        phie=pd.Series([0.2, 2.0]),
        sw=pd.Series([0.25, -1.0]),
        ng=pd.Series([0.5, 1.0]),
    )
    assert list(nrv) == [50.0, 100.0]
    assert list(pv) == [10.0, 100.0]
    assert list(hcpv) == [7.5, 100.0]


def test_validate_reports_missing_required_curve():
    issues = validate_reservoir_property_plan(pd.DataFrame({"DEPT": [1]}), ReservoirPropertyPlan())
    assert any(issue.code == "missing_required_curve" for issue in issues)
    assert reservoir_property_issue_table_rows(issues)


def test_run_reservoir_property_calculator_adds_output_curves_and_intervals():
    plan = ReservoirPropertyPlan(parameters=ReservoirPropertyParameters(area_m2=1000.0, oil_formation_volume_factor=1.25, gas_formation_volume_factor=0.01))
    result = run_reservoir_property_calculator(
        sample_df(),
        plan=plan,
        intervals=[{"name": "A", "top": 1000.0, "base": 1001.5}],
        source_references=("docs/sources/lab-4-property-cubes.pdf",),
    )
    assert result.schema == RESERVOIR_PROPERTY_CALCULATOR_SCHEMA
    assert not [issue for issue in result.issues if issue.severity == "error"]
    for curve in ["BRV", "NRV", "PV", "HCPV", "OOIP", "OGIP", "REC_OIL", "REC_GAS"]:
        assert curve in result.data.columns
    assert result.intervals[0].sample_count == 4
    assert result.intervals[0].gross_thickness == 1.5
    assert result.intervals[0].hydrocarbon_pore_volume_m3 > 0


def test_custom_curve_mapping_and_depth_window():
    data = sample_df().rename(columns={"PHIE": "POR_E", "SW_ARCHIE": "SW_SIM"})
    plan = ReservoirPropertyPlan(
        input_curves=ReservoirPropertyInputCurves(effective_porosity_curve="POR_E", water_saturation_curve="SW_SIM"),
        depth_top=1000.5,
        depth_base=1001.0,
    )
    result = run_reservoir_property_calculator(data, plan=plan)
    assert len(result.data) == 2
    assert result.intervals[0].top == 1000.5


def test_summarize_manifest_report_and_ui_rows():
    result = run_reservoir_property_calculator(sample_df())
    summaries = summarize_reservoir_volume_intervals(result.data, [{"name": "A", "top": 1000, "base": 1001}], result.plan)
    assert summaries[0].bulk_rock_volume_m3 > 0
    assert reservoir_volume_table_rows(summaries)
    manifest = build_reservoir_property_manifest(result)
    report = render_reservoir_property_markdown_report(result)
    assert manifest["schema"].endswith("/v1")
    assert "Reservoir Property Calculator Report" in report
    assert "Totals" in report
