import pandas as pd

from las_editor.petrophysical_workspace import (
    ArchieParameters,
    PetrophysicalCutoffSet,
    PetrophysicalInputCurves,
    PetrophysicalPlan,
    ShaleVolumeParameters,
    build_petrophysical_manifest,
    calculate_archie_water_saturation,
    calculate_effective_porosity,
    calculate_net_pay_flags,
    calculate_shale_volume,
    petrophysical_interval_table_rows,
    render_petrophysical_markdown_report,
    run_petrophysical_workspace,
    validate_petrophysical_plan,
)


def sample_df():
    return pd.DataFrame(
        {
            "DEPT": [1000.0, 1000.5, 1001.0, 1001.5],
            "GR": [40.0, 55.0, 100.0, 130.0],
            "POR": [0.22, 0.18, 0.08, 0.04],
            "RT": [25.0, 12.0, 3.0, 1.0],
        }
    )


def test_calculate_shale_volume_linear_clamps_values():
    result = calculate_shale_volume(pd.Series([35, 77.5, 120, 200]), ShaleVolumeParameters(gr_clean=35, gr_shale=120))
    assert list(result.round(3)) == [0.0, 0.5, 1.0, 1.0]


def test_calculate_effective_porosity_corrects_by_vsh():
    result = calculate_effective_porosity(pd.Series([0.2, 0.2]), pd.Series([0.0, 0.5]))
    assert list(result.round(3)) == [0.2, 0.1]


def test_archie_water_saturation_is_clamped():
    sw = calculate_archie_water_saturation(pd.Series([0.2, 0.01]), pd.Series([20.0, 1.0]), ArchieParameters(rw=0.1))
    assert sw.iloc[0] < 1.0
    assert sw.iloc[1] <= 1.0


def test_run_petrophysical_workspace_adds_output_curves_and_intervals():
    plan = PetrophysicalPlan(cutoffs=PetrophysicalCutoffSet(shale_volume_max=0.5, effective_porosity_min=0.1, water_saturation_max=0.7, resistivity_min=5))
    result = run_petrophysical_workspace(
        sample_df(),
        plan=plan,
        intervals=[{"name": "A", "top": 1000.0, "base": 1001.5}],
        source_references=("docs/sources/application-of-mud-gas-analysis-for-reservoir-evaluation.pdf",),
    )
    assert not result.issues
    for curve in ["VSH", "PHIE", "SW_ARCHIE", "SO", "RES", "NET", "PAY", "NG"]:
        assert curve in result.data.columns
    assert result.intervals[0].sample_count == 4
    assert result.intervals[0].gross_thickness == 1.5


def test_validate_petrophysical_plan_reports_missing_curve():
    issues = validate_petrophysical_plan(pd.DataFrame({"GR": [50]}), PetrophysicalPlan())
    assert any(issue.code == "missing_required_curve" for issue in issues)


def test_calculate_net_pay_flags_uses_cutoffs():
    reservoir, net, pay = calculate_net_pay_flags(
        vsh=pd.Series([0.2, 0.7]),
        phie=pd.Series([0.15, 0.2]),
        sw=pd.Series([0.4, 0.4]),
        rt=pd.Series([20, 20]),
        cutoffs=PetrophysicalCutoffSet(),
    )
    assert list(reservoir) == [1, 0]
    assert list(net) == [1, 0]
    assert list(pay) == [1, 0]


def test_manifest_and_report_are_rendered():
    result = run_petrophysical_workspace(sample_df())
    manifest = build_petrophysical_manifest(result)
    report = render_petrophysical_markdown_report(result)
    assert manifest["schema"].endswith("/v1")
    assert "Petrophysical Workspace Summary" in report
    assert petrophysical_interval_table_rows(result.intervals)
