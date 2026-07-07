import pandas as pd

from las_editor.petrophysical_crossplot_workspace import (
    PETROPHYSICAL_CROSSPLOT_SCHEMA,
    CrossplotInputCurves,
    CrossplotPlan,
    build_crossplot_spec,
    build_petrophysical_crossplot_manifest,
    calculate_linear_trend,
    crossplot_cluster_table_rows,
    crossplot_issue_table_rows,
    crossplot_spec_table_rows,
    filter_crossplot_depth_window,
    render_petrophysical_crossplot_markdown_report,
    run_petrophysical_crossplot_workspace,
    summarize_crossplot_clusters,
    validate_crossplot_plan,
)


def sample_df():
    return pd.DataFrame(
        {
            "DEPT": [1000.0, 1000.5, 1001.0, 1001.5, 1002.0],
            "PHIE": [0.22, 0.18, 0.15, 0.10, 0.06],
            "RT": [30.0, 18.0, 10.0, 4.0, 2.0],
            "SW_ARCHIE": [0.25, 0.35, 0.50, 0.75, 0.90],
            "VSH": [0.08, 0.20, 0.32, 0.50, 0.72],
            "RHOB": [2.25, 2.32, 2.40, 2.50, 2.62],
            "NPHI": [0.28, 0.24, 0.18, 0.12, 0.08],
            "DT": [90.0, 82.0, 75.0, 68.0, 60.0],
            "GR": [35.0, 55.0, 80.0, 110.0, 140.0],
        }
    )


def test_validate_crossplot_plan_reports_missing_curve():
    issues = validate_crossplot_plan(pd.DataFrame({"PHIE": [0.2]}), CrossplotPlan(plots=("pickett",)))
    assert any(issue.code == "missing_required_curve" for issue in issues)
    assert crossplot_issue_table_rows(issues)


def test_depth_window_filters_data():
    filtered = filter_crossplot_depth_window(sample_df(), CrossplotPlan(depth_top=1000.5, depth_base=1001.5))
    assert list(filtered["DEPT"]) == [1000.5, 1001.0, 1001.5]


def test_linear_trend_returns_r_squared():
    trend = calculate_linear_trend(pd.DataFrame({"x": [1, 2, 3], "y": [2, 4, 6]}))
    assert trend.slope == 2.0
    assert trend.intercept == 0.0
    assert trend.r_squared == 1.0


def test_cluster_summary_uses_color_buckets():
    table = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6], "color": [0.1, 0.3, 0.7], "depth": [10, 11, 12]})
    clusters = summarize_crossplot_clusters(table, low_cutoff=0.25, high_cutoff=0.45, color_label="VSH")
    assert [cluster.cluster_name for cluster in clusters] == ["Low VSH", "Medium VSH", "High VSH"]


def test_build_pickett_spec_has_expected_axes():
    spec = build_crossplot_spec(sample_df(), "pickett", CrossplotPlan())
    assert spec.name == "pickett"
    assert spec.x_curve == "PHIE"
    assert spec.y_curve == "RT"
    assert spec.y_scale == "log"
    assert spec.point_count == 5


def test_run_petrophysical_crossplot_workspace_builds_all_specs_and_report():
    result = run_petrophysical_crossplot_workspace(
        sample_df(),
        source_references=("docs/sources/lab-4-property-cubes.pdf",),
    )
    assert result.schema == PETROPHYSICAL_CROSSPLOT_SCHEMA
    assert not [issue for issue in result.issues if issue.severity == "error"]
    assert len(result.specs) == 5
    assert crossplot_spec_table_rows(result.specs)
    assert crossplot_cluster_table_rows(result.specs)
    manifest = build_petrophysical_crossplot_manifest(result)
    report = render_petrophysical_crossplot_markdown_report(result)
    assert manifest["spec_count"] == 5
    assert "Petrophysical Crossplot Workspace Report" in report


def test_custom_mapping_and_selected_plots():
    data = sample_df().rename(columns={"PHIE": "POR_E", "RT": "RDEEP"})
    plan = CrossplotPlan(
        input_curves=CrossplotInputCurves(porosity_curve="POR_E", resistivity_curve="RDEEP"),
        plots=("pickett", "gr_resistivity"),
    )
    result = run_petrophysical_crossplot_workspace(data, plan=plan)
    assert len(result.specs) == 2
    assert result.specs[0].x_curve == "POR_E"


def test_invalid_plot_returns_error_result():
    result = run_petrophysical_crossplot_workspace(sample_df(), plan=CrossplotPlan(plots=("unknown",)))
    assert not result.specs
    assert any(issue.code == "unsupported_plot" for issue in result.issues)
