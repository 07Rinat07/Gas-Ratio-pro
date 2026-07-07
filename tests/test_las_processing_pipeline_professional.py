import pandas as pd

from las_editor.las_processing_pipeline import (
    LasProcessingOperation,
    apply_processing_pipeline,
    build_processing_manifest,
    build_processing_plan,
    preview_processing_pipeline,
    render_processing_report,
)


def sample_df():
    return pd.DataFrame(
        {
            "DEPT": [1000.0, 1000.5, 1001.0, 1001.5, 1002.0],
            "GR": [80.0, 82.0, 300.0, 84.0, 86.0],
            "POR": [0.10, -999.25, 0.20, 0.25, 0.30],
        }
    )


def test_build_processing_plan_validates_operations():
    plan = build_processing_plan(
        sample_df(),
        [LasProcessingOperation("moving_average", curve="GR", parameters={"window": 3})],
    )
    assert not plan.issues
    assert plan.operations[0].operation == "moving_average"
    assert plan.operations[0].curve == "GR"


def test_processing_plan_rejects_missing_curve():
    plan = build_processing_plan(
        sample_df(),
        [LasProcessingOperation("moving_average", curve="BAD", parameters={"window": 3})],
    )
    assert any(issue.code == "curve_not_found" for issue in plan.issues)


def test_apply_processing_pipeline_adds_filtered_curve():
    result = apply_processing_pipeline(
        sample_df(),
        [LasProcessingOperation("median_filter", curve="GR", output_curve="GR_MED", parameters={"window": 3})],
    )
    assert "GR_MED" in result.data.columns
    assert len(result.history) == 1
    assert result.data.loc[2, "GR_MED"] < 300.0


def test_despike_corrects_spike_to_median_baseline():
    result = apply_processing_pipeline(
        sample_df(),
        [LasProcessingOperation("despike", curve="GR", output_curve="GR_DSPK", parameters={"threshold": 50.0, "window": 3})],
    )
    assert result.data.loc[2, "GR_DSPK"] < 300.0


def test_fill_nulls_linear_replaces_las_null_value():
    result = apply_processing_pipeline(
        sample_df(),
        [LasProcessingOperation("fill_nulls", curve="POR", output_curve="POR_FILL", parameters={"method": "linear"})],
    )
    assert result.data["POR_FILL"].isna().sum() == 0
    assert result.data.loc[1, "POR_FILL"] != -999.25


def test_normalization_and_clip_operations():
    result = apply_processing_pipeline(
        sample_df(),
        [
            LasProcessingOperation("normalize_minmax", curve="GR", output_curve="GR_MM"),
            LasProcessingOperation("clip_range", curve="GR", output_curve="GR_CLIP", parameters={"min": 0, "max": 100}),
        ],
    )
    assert result.data["GR_MM"].min() == 0
    assert result.data["GR_MM"].max() == 1
    assert result.data["GR_CLIP"].max() == 100


def test_resample_depth_changes_depth_step():
    result = apply_processing_pipeline(
        sample_df(),
        [LasProcessingOperation("resample_depth", parameters={"step": 0.25})],
        depth_curve="DEPT",
    )
    assert len(result.data) == 9
    assert result.data.loc[1, "DEPT"] == 1000.25


def test_preview_manifest_and_markdown_report_are_available():
    result = apply_processing_pipeline(
        sample_df(),
        [LasProcessingOperation("moving_average", curve="GR", output_curve="GR_MA", parameters={"window": 3})],
    )
    manifest = build_processing_manifest(result)
    preview = preview_processing_pipeline(sample_df(), [LasProcessingOperation("moving_average", curve="GR", parameters={"window": 3})])
    report = render_processing_report(result)
    assert manifest["schema"].endswith("las-processing-pipeline/v1")
    assert preview["output_shape"][0] == 5
    assert "LAS Processing Pipeline Report" in report
