import pandas as pd

from las_editor.depth_repair import analyze_depth_order, repair_depth_order, render_depth_repair_report


def test_depth_repair_sorts_rows_without_mutating_original_measurements() -> None:
    df = pd.DataFrame(
        {
            "DEPT": [1000.0, 1001.0, 1000.5],
            "GR": [80.0, 90.0, 85.0],
            "C1": [10.0, 30.0, 20.0],
        }
    )

    result = repair_depth_order(df)

    assert list(df["DEPT"]) == [1000.0, 1001.0, 1000.5]
    assert list(result.data["DEPT"]) == [1000.0, 1000.5, 1001.0]
    assert list(result.data["GR"]) == [80.0, 85.0, 90.0]
    assert list(result.data["C1"]) == [10.0, 20.0, 30.0]
    assert result.history[-1].details["measurement_policy"] == "all_curves_move_with_their_original_depth_rows"
    assert result.manifest["schema"].endswith("depth-repair/v1")


def test_depth_repair_noop_when_depth_is_already_increasing() -> None:
    df = pd.DataFrame({"DEPTH": [1.0, 2.0, 3.0], "RHOB": [2.3, 2.4, 2.5]})

    result = repair_depth_order(df)

    assert result.plan.required is False
    assert result.history == ()
    assert result.data.equals(df)
    assert "no repair" in result.diagnostics[0].lower()


def test_depth_repair_reports_duplicate_and_null_depths() -> None:
    df = pd.DataFrame({"DEPT": [1000.0, 1000.0, None, 999.5], "GR": [1, 2, 3, 4]})

    plan = analyze_depth_order(df)
    codes = {issue.code for issue in plan.issues}
    result = repair_depth_order(df, fail_on_errors=False)
    report = render_depth_repair_report(result)

    assert "DUPLICATE_DEPTH" in codes
    assert "NULL_DEPTH" in codes
    assert plan.required is True
    assert "Depth Repair Report" in report
