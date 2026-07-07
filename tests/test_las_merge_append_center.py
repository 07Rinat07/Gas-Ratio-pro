from __future__ import annotations

import pandas as pd

from las_editor.las_merge_append_center import append_las_depth_intervals, insert_las_curves_from_las


def test_append_las_depth_intervals_creates_working_copy_and_sorts_by_depth():
    base = pd.DataFrame({"DEPT": [100.0, 101.0], "GR": [50.0, 55.0]})
    incoming = pd.DataFrame({"DEPTH": [103.0, 102.0], "RHOB": [2.45, 2.40]})

    result = append_las_depth_intervals(base, incoming, duplicate_depth_policy="keep_all")

    assert result.data["DEPT"].tolist() == [100.0, 101.0, 102.0, 103.0]
    assert "GR" in result.data.columns
    assert "RHOB" in result.data.columns
    assert base.columns.tolist() == ["DEPT", "GR"]
    assert incoming.columns.tolist() == ["DEPTH", "RHOB"]
    assert result.manifest["safety"]["original_data_mutated"] is False


def test_append_las_depth_intervals_handles_duplicate_policy_keep_last():
    base = pd.DataFrame({"DEPT": [100.0, 101.0], "GR": [50.0, 55.0]})
    incoming = pd.DataFrame({"DEPT": [101.0, 102.0], "GR": [60.0, 65.0]})

    result = append_las_depth_intervals(base, incoming, duplicate_depth_policy="keep_last")

    assert result.data["DEPT"].tolist() == [100.0, 101.0, 102.0]
    assert result.data.loc[result.data["DEPT"] == 101.0, "GR"].iloc[0] == 60.0
    assert any(issue.code == "DUPLICATE_DEPTH" for issue in result.issues)


def test_insert_las_curves_from_las_interpolates_source_curves_without_mutation():
    target = pd.DataFrame({"DEPT": [100.0, 101.0, 102.0], "GR": [50.0, 55.0, 60.0]})
    source = pd.DataFrame({"DEPTH": [100.0, 102.0], "RHOB": [2.40, 2.60], "NPHI": [0.30, 0.20]})

    result = insert_las_curves_from_las(target, source, curves=["RHOB"], match_policy="interpolate")

    assert "RHOB" in result.data.columns
    assert result.data["RHOB"].tolist() == [2.40, 2.50, 2.60]
    assert "RHOB" not in target.columns
    assert source.columns.tolist() == ["DEPTH", "RHOB", "NPHI"]
    assert result.manifest["operation"] == "insert_las_curves_from_las"
