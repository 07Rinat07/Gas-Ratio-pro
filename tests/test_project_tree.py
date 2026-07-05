from __future__ import annotations

import pandas as pd

from projects import (
    build_project_tree,
    create_project,
    flatten_project_tree,
    project_tree_table_rows,
    save_project_calculation,
    save_project_export,
    save_project_las_file,
)


def test_project_tree_groups_saved_project_objects_without_reading_raw_tables(tmp_path):
    project = create_project(tmp_path, name="Demo Project", description="Tree test", project_id="demo")
    save_project_las_file(
        b"~Version\nVERS. 2.0\n~Well\nNULL. -999.25\n~Curve\nDEPT.M : Depth\nC1. : C1\n~Ascii\n1000 80\n",
        root=tmp_path,
        project_id=project.id,
        file_name="well_a.las",
        well_name="Well A",
        version_label="Raw LAS",
    )
    save_project_calculation(
        pd.DataFrame({"depth": [1000.0, 1001.0], "c1": [80.0, 81.0]}),
        root=tmp_path,
        project_id=project.id,
        source_label="Well A calculation",
        warnings=("check mapping",),
    )
    save_project_export(
        b"<html>report</html>",
        root=tmp_path,
        project_id=project.id,
        label="Interval report",
        file_name="interval.html",
        mime_type="text/html",
        kind="html_report",
    )

    tree = build_project_tree(tmp_path, project.id)
    flat = flatten_project_tree(tree)
    labels = [node.label for _level, node in flat]
    kinds = [node.kind for _level, node in flat]

    assert tree.label == "Demo Project"
    assert tree.metadata["project_id"] == "demo"
    assert "Скважины" in labels
    assert "Расчеты" in labels
    assert "Отчеты и экспорты" in labels
    assert "Well A" in labels
    assert "Raw LAS" in labels
    assert "Well A calculation" in labels
    assert "Interval report" in labels
    assert "well" in kinds
    assert "las_version" in kinds
    assert "calculation" in kinds
    assert "export" in kinds


def test_project_tree_returns_empty_folders_for_new_project(tmp_path):
    project = create_project(tmp_path, name="Empty Project", project_id="empty")

    tree = build_project_tree(tmp_path, project.id)
    rows = project_tree_table_rows(tree)
    empty_labels = {row["label"] for row in rows if row["kind"] == "empty"}

    assert empty_labels == {
        "Нет сохраненных скважин",
        "Нет сохраненных расчетов",
        "Нет сохраненных экспортов",
    }
    assert rows[0]["label"] == "Empty Project"


def test_project_tree_groups_wells_by_saved_assignments(tmp_path):
    project = create_project(tmp_path, name="Grouped Project", project_id="grouped")
    save_project_las_file(
        b"~Version\nVERS. 2.0\n~Well\nNULL. -999.25\n~Curve\nDEPT.M : Depth\nC1. : C1\n~Ascii\n1000 80\n",
        root=tmp_path,
        project_id=project.id,
        file_name="north_1.las",
        well_name="North 1",
        version_label="Raw LAS",
    )
    save_project_las_file(
        b"~Version\nVERS. 2.0\n~Well\nNULL. -999.25\n~Curve\nDEPT.M : Depth\nC1. : C1\n~Ascii\n1000 90\n",
        root=tmp_path,
        project_id=project.id,
        file_name="south_1.las",
        well_name="South 1",
        version_label="Raw LAS",
    )

    from projects import save_project_well_group

    save_project_well_group(
        root=tmp_path,
        project_id=project.id,
        name="Северный куст",
        well_ids=("north-1",),
        description="Рабочая группа северного участка",
    )

    tree = build_project_tree(tmp_path, project.id)
    rows = project_tree_table_rows(tree)
    labels = [str(row["label"]) for row in rows]
    kinds = [str(row["kind"]) for row in rows]

    assert "Северный куст" in labels
    assert "Без группы" in labels
    assert labels.index("Северный куст") < labels.index("North 1")
    assert labels.index("Без группы") < labels.index("South 1")
    assert "well_group" in kinds


def test_well_group_assignment_moves_wells_between_groups(tmp_path):
    project = create_project(tmp_path, name="Group Move", project_id="group-move")

    from projects import assign_project_wells_to_group, list_project_well_groups, save_project_well_group

    save_project_well_group(tmp_path, project.id, name="A", well_ids=("well-1", "well-2"), group_id="a")
    save_project_well_group(tmp_path, project.id, name="B", well_ids=("well-3",), group_id="b")

    updated = assign_project_wells_to_group(tmp_path, project.id, "b", ("well-2",))
    groups = {group.id: group for group in list_project_well_groups(tmp_path, project.id)}

    assert updated.well_ids == ("well-3", "well-2")
    assert groups["a"].well_ids == ("well-1",)
    assert groups["b"].well_ids == ("well-3", "well-2")
