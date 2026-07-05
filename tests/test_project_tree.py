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
    las_record = save_project_las_file(
        b"~Version\nVERS. 2.0\n~Well\nNULL. -999.25\n~Curve\nDEPT.M : Depth\nC1. : C1\n~Ascii\n1000 80\n",
        root=tmp_path,
        project_id=project.id,
        file_name="well_a.las",
        well_name="Well A",
        version_label="Raw LAS",
    )
    calculation_record = save_project_calculation(
        pd.DataFrame({"depth": [1000.0, 1001.0], "c1": [80.0, 81.0]}),
        root=tmp_path,
        project_id=project.id,
        source_label="Well A calculation",
        warnings=("check mapping",),
    )
    export_record = save_project_export(
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
    assert "Папки" in labels
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
        "Нет пользовательских папок",
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


def test_project_tree_shows_custom_project_folders_with_metadata_refs(tmp_path):
    project = create_project(tmp_path, name="Folder Project", project_id="foldered")
    las_record = save_project_las_file(
        b"~Version\nVERS. 2.0\n~Well\nNULL. -999.25\n~Curve\nDEPT.M : Depth\nC1. : C1\n~Ascii\n1000 80\n",
        root=tmp_path,
        project_id=project.id,
        file_name="well_a.las",
        well_name="Well A",
        version_label="Raw LAS",
    )
    calculation_record = save_project_calculation(
        pd.DataFrame({"depth": [1000.0], "c1": [80.0]}),
        root=tmp_path,
        project_id=project.id,
        source_label="Well A calculation",
        warnings=(),
    )

    from projects import save_project_folder

    save_project_folder(
        root=tmp_path,
        project_id=project.id,
        name="Рабочий набор",
        item_ids=(f"well:{las_record.well_id}", f"calculation:{calculation_record.id}"),
        description="Папка для текущей проверки",
    )

    rows = project_tree_table_rows(build_project_tree(tmp_path, project.id))
    labels = [str(row["label"]) for row in rows]
    kinds = [str(row["kind"]) for row in rows]

    assert "Папки" in labels
    assert "Рабочий набор" in labels
    assert "Well A" in labels
    assert "Well A calculation" in labels
    assert "custom_folder" in kinds
    assert "folder_item" in kinds
    assert labels.index("Рабочий набор") < labels.index("Well A calculation")


def test_assign_project_items_to_folder_replaces_folder_contents(tmp_path):
    project = create_project(tmp_path, name="Assign Folder", project_id="assign-folder")

    from projects import assign_project_items_to_folder, save_project_folder

    save_project_folder(
        root=tmp_path,
        project_id=project.id,
        name="Контроль",
        folder_id="control",
        item_ids=("well:old",),
    )

    updated = assign_project_items_to_folder(
        root=tmp_path,
        project_id=project.id,
        folder_id="control",
        item_ids=("well:new", "calculation:latest", "well:new"),
    )

    assert updated.item_ids == ("well:new", "calculation:latest")


def test_project_explorer_move_options_include_safe_metadata_objects(tmp_path):
    project = create_project(tmp_path, name="Move Options", project_id="move-options")
    las_record = save_project_las_file(
        b"~Version\nVERS. 2.0\n~Well\nNULL. -999.25\n~Curve\nDEPT.M : Depth\nC1. : C1\n~Ascii\n1000 80\n",
        root=tmp_path,
        project_id=project.id,
        file_name="well_a.las",
        well_name="Well A",
        version_label="Raw LAS",
    )
    calculation_record = save_project_calculation(
        pd.DataFrame({"depth": [1000.0], "c1": [80.0]}),
        root=tmp_path,
        project_id=project.id,
        source_label="Well A calculation",
    )
    export_record = save_project_export(
        b"csv,data",
        root=tmp_path,
        project_id=project.id,
        label="CSV export",
        file_name="export.csv",
        mime_type="text/csv",
        kind="csv",
    )

    from projects import list_project_explorer_move_options

    options = list_project_explorer_move_options(tmp_path, project.id)
    option_ids = {option.id for option in options}
    option_targets = {option.id: option.target_type for option in options}

    assert f"well:{las_record.well_id}" in option_ids
    assert f"las:{las_record.id}" in option_ids
    assert f"calculation:{calculation_record.id}" in option_ids
    assert f"export:{export_record.id}" in option_ids
    assert option_targets[f"well:{las_record.well_id}"] == "well_group_or_folder"
    assert option_targets[f"calculation:{calculation_record.id}"] == "folder"


def test_project_explorer_move_item_to_folder_appends_without_duplicates(tmp_path):
    project = create_project(tmp_path, name="Folder Move", project_id="folder-move")

    from projects import list_project_folders, move_project_explorer_item_to_folder, save_project_folder

    save_project_folder(
        root=tmp_path,
        project_id=project.id,
        name="Контроль",
        folder_id="control",
        item_ids=("well:old",),
    )

    first = move_project_explorer_item_to_folder(tmp_path, project.id, "calculation:latest", "control")
    second = move_project_explorer_item_to_folder(tmp_path, project.id, "calculation:latest", "control")
    folders = {folder.id: folder for folder in list_project_folders(tmp_path, project.id)}

    assert first.message == "Объект добавлен в папку: Контроль"
    assert second.updated_folder is not None
    assert folders["control"].item_ids == ("well:old", "calculation:latest")


def test_project_explorer_move_well_to_group_updates_group_assignment(tmp_path):
    project = create_project(tmp_path, name="Group Move UI", project_id="group-move-ui")

    from projects import (
        list_project_well_groups,
        move_project_explorer_well_to_group,
        save_project_well_group,
    )

    save_project_well_group(tmp_path, project.id, name="Север", well_ids=("well-1", "well-2"), group_id="north")
    save_project_well_group(tmp_path, project.id, name="Юг", well_ids=(), group_id="south")

    result = move_project_explorer_well_to_group(tmp_path, project.id, "well:well-2", "south")
    groups = {group.id: group for group in list_project_well_groups(tmp_path, project.id)}

    assert result.message == "Скважина перемещена в группу: Юг"
    assert groups["north"].well_ids == ("well-1",)
    assert groups["south"].well_ids == ("well-2",)


def test_project_explorer_rejects_non_well_group_move(tmp_path):
    project = create_project(tmp_path, name="Bad Group Move", project_id="bad-group-move")

    from projects import move_project_explorer_well_to_group, save_project_well_group

    save_project_well_group(tmp_path, project.id, name="Группа", well_ids=(), group_id="group")

    try:
        move_project_explorer_well_to_group(tmp_path, project.id, "calculation:abc", "group")
    except ValueError as exc:
        assert "только объект скважины" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-well move into a well group")


def test_project_tree_applies_color_labels_to_project_objects(tmp_path):
    project = create_project(tmp_path, name="Labels", project_id="labels")
    las_record = save_project_las_file(
        b"~Version\nVERS. 2.0\n~Well\nNULL. -999.25\n~Curve\nDEPT.M : Depth\nC1. : C1\n~Ascii\n1000 80\n",
        root=tmp_path,
        project_id=project.id,
        file_name="well_a.las",
        well_name="Well A",
        version_label="Raw LAS",
    )

    from projects import set_project_explorer_label

    set_project_explorer_label(
        root=tmp_path,
        project_id=project.id,
        object_id=f"well:{las_record.well_id}",
        color="green",
        note="ready for review",
    )

    rows = project_tree_table_rows(build_project_tree(tmp_path, project.id))
    well_row = next(row for row in rows if row["id"] == f"well:{las_record.well_id}")

    assert well_row["color_label"] == "green"
    assert well_row["color_label_name"] == "Зеленая"
    assert well_row["color_label_icon"] == "🟢"


def test_project_tree_folder_items_inherit_source_color_labels(tmp_path):
    project = create_project(tmp_path, name="Folder Label", project_id="folder-label")
    calculation_record = save_project_calculation(
        pd.DataFrame({"depth": [1000.0], "c1": [80.0]}),
        root=tmp_path,
        project_id=project.id,
        source_label="Marked calculation",
    )

    from projects import save_project_folder, set_project_explorer_label

    object_id = f"calculation:{calculation_record.id}"
    save_project_folder(tmp_path, project.id, name="Review", item_ids=(object_id,), folder_id="review")
    set_project_explorer_label(tmp_path, project.id, object_id=object_id, color="purple")

    rows = project_tree_table_rows(build_project_tree(tmp_path, project.id))
    folder_item_row = next(row for row in rows if row["kind"] == "folder_item")

    assert folder_item_row["label"] == "Marked calculation"
    assert folder_item_row["color_label"] == "purple"
    assert folder_item_row["color_label_icon"] == "🟣"


def test_project_explorer_color_label_can_be_cleared(tmp_path):
    project = create_project(tmp_path, name="Clear Label", project_id="clear-label")

    from projects import clear_project_explorer_label, list_project_explorer_labels, set_project_explorer_label

    set_project_explorer_label(tmp_path, project.id, object_id="export:report", color="blue")
    assert len(list_project_explorer_labels(tmp_path, project.id)) == 1

    removed = clear_project_explorer_label(tmp_path, project.id, object_id="export:report")

    assert removed is True
    assert list_project_explorer_labels(tmp_path, project.id) == ()


def test_project_well_card_can_be_saved_and_listed_without_las_payload(tmp_path):
    project = create_project(tmp_path, name="Well Cards", project_id="well-cards")

    from projects import build_project_well_card_table, list_project_well_cards, save_project_well_card

    card = save_project_well_card(
        root=tmp_path,
        project_id=project.id,
        well_id="well-1",
        name="Well 1",
        status="review",
        note="Check source LAS header",
    )
    cards = list_project_well_cards(tmp_path, project.id)
    rows = build_project_well_card_table(tmp_path, project.id)

    assert card.status_label == "На проверке"
    assert len(cards) == 1
    assert cards[0].well_id == "well-1"
    assert cards[0].note == "Check source LAS header"
    assert rows[0].status_label == "На проверке"


def test_project_well_card_update_preserves_created_at_and_changes_metadata(tmp_path):
    project = create_project(tmp_path, name="Well Card Update", project_id="well-card-update")

    from projects import get_project_well_card, save_project_well_card

    first = save_project_well_card(tmp_path, project.id, well_id="well-2", name="Well 2", status="draft")
    second = save_project_well_card(
        tmp_path,
        project.id,
        well_id="well-2",
        name="Well 2A",
        status="ready",
        note="Approved metadata",
        metadata={"source": "manual"},
    )
    stored = get_project_well_card(tmp_path, project.id, "well-2")

    assert second.created_at == first.created_at
    assert second.updated_at >= first.updated_at
    assert stored is not None
    assert stored.name == "Well 2A"
    assert stored.status_label == "Готова"
    assert stored.metadata == {"source": "manual"}


def test_project_tree_shows_saved_well_card_status(tmp_path):
    project = create_project(tmp_path, name="Tree Well Card", project_id="tree-well-card")
    las_record = save_project_las_file(
        b"~Version\nVERS. 2.0\n~Well\nNULL. -999.25\n~Curve\nDEPT.M : Depth\nC1. : C1\n~Ascii\n1000 80\n",
        root=tmp_path,
        project_id=project.id,
        file_name="well_card.las",
        well_name="Well Card",
        version_label="Raw LAS",
    )

    from projects import save_project_well_card

    save_project_well_card(
        tmp_path,
        project.id,
        well_id=las_record.well_id,
        name="Well Card Official",
        status="ready",
    )

    rows = project_tree_table_rows(build_project_tree(tmp_path, project.id))
    well_row = next(row for row in rows if row["id"] == f"well:{las_record.well_id}")

    assert well_row["label"] == "Well Card Official"
    assert "карточка: Готова" in str(well_row["status"])


def test_project_well_card_coordinates_are_validated_and_listed(tmp_path):
    project = create_project(tmp_path, name="Well Coordinates", project_id="well-coordinates")

    from projects import (
        build_project_well_card_table,
        get_project_well_card,
        merge_project_well_coordinates_metadata,
        save_project_well_card,
    )

    metadata = merge_project_well_coordinates_metadata(
        {"source": "manual"},
        x="502341.25",
        y="6154321.5",
        latitude="47.123456",
        longitude="71.654321",
    )
    save_project_well_card(
        tmp_path,
        project.id,
        well_id="well-coord",
        name="Well Coord",
        status="review",
        metadata=metadata,
    )

    stored = get_project_well_card(tmp_path, project.id, "well-coord")
    rows = build_project_well_card_table(tmp_path, project.id)

    assert stored is not None
    assert stored.metadata["source"] == "manual"
    assert stored.coordinates.x == 502341.25
    assert stored.coordinates.y == 6154321.5
    assert stored.coordinates.latitude == 47.123456
    assert stored.coordinates.longitude == 71.654321
    assert rows[0].coordinate_x == 502341.25
    assert rows[0].coordinate_y == 6154321.5
    assert rows[0].latitude == 47.123456
    assert rows[0].longitude == 71.654321
    assert "X=502341.25" in rows[0].coordinates_label
    assert "47.123456, 71.654321" in rows[0].coordinates_label


def test_project_well_card_rejects_invalid_geographic_coordinates(tmp_path):
    project = create_project(tmp_path, name="Bad Coordinates", project_id="bad-coordinates")

    from projects import merge_project_well_coordinates_metadata, save_project_well_card

    try:
        metadata = merge_project_well_coordinates_metadata(latitude="91", longitude="71")
    except ValueError as exc:
        assert "Широта" in str(exc)
    else:  # pragma: no cover - defensive assertion for plain pytest without raises helper
        raise AssertionError("Invalid latitude was accepted")

    try:
        metadata = merge_project_well_coordinates_metadata(latitude="47", longitude="181")
    except ValueError as exc:
        assert "Долгота" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Invalid longitude was accepted")

    assert save_project_well_card(tmp_path, project.id, well_id="safe-well", name="Safe Well").metadata == {}


def test_project_tree_shows_well_card_coordinates_in_status(tmp_path):
    project = create_project(tmp_path, name="Tree Coordinates", project_id="tree-coordinates")
    las_record = save_project_las_file(
        b"~Version\nVERS. 2.0\n~Well\nNULL. -999.25\n~Curve\nDEPT.M : Depth\nC1. : C1\n~Ascii\n1000 80\n",
        root=tmp_path,
        project_id=project.id,
        file_name="well_coord.las",
        well_name="Well Coord",
        version_label="Raw LAS",
    )

    from projects import merge_project_well_coordinates_metadata, save_project_well_card

    save_project_well_card(
        tmp_path,
        project.id,
        well_id=las_record.well_id,
        name="Well Coord Official",
        status="ready",
        metadata=merge_project_well_coordinates_metadata(x=100.5, y=200.25, latitude=47, longitude=71),
    )

    rows = project_tree_table_rows(build_project_tree(tmp_path, project.id))
    well_row = next(row for row in rows if row["id"] == f"well:{las_record.well_id}")

    assert "координаты: X=100.5; Y=200.25; 47.000000, 71.000000" in str(well_row["status"])


def test_project_well_card_kb_is_validated_and_listed(tmp_path):
    project = create_project(tmp_path, name="Well KB", project_id="well-kb")

    from projects import (
        build_project_well_card_table,
        get_project_well_card,
        merge_project_well_kb_metadata,
        save_project_well_card,
    )

    metadata = merge_project_well_kb_metadata({"source": "manual"}, kb_m="12,75")
    save_project_well_card(
        tmp_path,
        project.id,
        well_id="well-kb",
        name="Well KB",
        status="review",
        metadata=metadata,
    )

    stored = get_project_well_card(tmp_path, project.id, "well-kb")
    rows = build_project_well_card_table(tmp_path, project.id)

    assert stored is not None
    assert stored.metadata["source"] == "manual"
    assert stored.depth_reference.kb_m == 12.75
    assert stored.depth_reference.kb_label == "KB=12.750 м"
    assert rows[0].kb_m == 12.75
    assert rows[0].kb_label == "KB=12.750 м"


def test_project_well_card_rejects_invalid_kb(tmp_path):
    project = create_project(tmp_path, name="Bad KB", project_id="bad-kb")

    from projects import merge_project_well_kb_metadata, save_project_well_card

    try:
        merge_project_well_kb_metadata(kb_m="10001")
    except ValueError as exc:
        assert "KB" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Invalid KB was accepted")

    assert save_project_well_card(tmp_path, project.id, well_id="safe-kb", name="Safe KB").metadata == {}


def test_project_tree_shows_well_card_kb_in_status(tmp_path):
    project = create_project(tmp_path, name="Tree KB", project_id="tree-kb")
    las_record = save_project_las_file(
        b"~Version\nVERS. 2.0\n~Well\nNULL. -999.25\n~Curve\nDEPT.M : Depth\nC1. : C1\n~Ascii\n1000 80\n",
        root=tmp_path,
        project_id=project.id,
        file_name="well_kb.las",
        well_name="Well KB",
        version_label="Raw LAS",
    )

    from projects import merge_project_well_kb_metadata, save_project_well_card

    save_project_well_card(
        tmp_path,
        project.id,
        well_id=las_record.well_id,
        name="Well KB Official",
        status="ready",
        metadata=merge_project_well_kb_metadata(kb_m="15"),
    )

    rows = project_tree_table_rows(build_project_tree(tmp_path, project.id))
    well_row = next(row for row in rows if row["id"] == f"well:{las_record.well_id}")

    assert "KB=15 м" in str(well_row["status"])
