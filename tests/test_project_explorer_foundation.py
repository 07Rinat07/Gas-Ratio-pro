from projects.project_explorer_foundation import (
    OperationStatus,
    ProjectObjectType,
    build_operation_entry,
    build_project_explorer_state,
    explorer_table_rows,
    las_workspace_actions_for_node,
    operation_journal_rows,
    undo_redo_state,
)


def test_project_explorer_builds_wells_las_and_curves_tree():
    state = build_project_explorer_state(
        project_id="demo",
        project_name="Demo Project",
        wells=[
            {
                "id": "Well-001",
                "name": "Well-001",
                "las_files": [
                    {"id": "main", "name": "main.las", "curves": ["DEPT", "GR", "GAS_SUM"]}
                ],
            }
        ],
        sources_count=2,
        templates_count=3,
        selected_node_id="las:well_001:main",
    )

    rows = explorer_table_rows(state)
    assert state.schema == "gas-ratio-pro.project-explorer.v1"
    assert any(row["title"] == "Well-001" and row["object_type"] == "well" for row in rows)
    assert any(row["title"] == "main.las" and row["object_type"] == "las" for row in rows)
    assert any(row["title"] == "GAS_SUM" and row["object_type"] == "curve" for row in rows)
    assert state.selected_node().object_type == ProjectObjectType.LAS


def test_las_context_actions_are_available_from_selected_las_node():
    state = build_project_explorer_state(
        project_id="demo",
        project_name="Demo Project",
        wells=[{"id": "W1", "name": "W1", "las_files": [{"id": "L1", "name": "L1.las"}]}],
        selected_node_id="las:w1:l1",
    )

    actions = las_workspace_actions_for_node(state.selected_node())
    action_ids = {action.action_id for action in actions}
    assert {"append_curves", "merge_las", "depth_repair", "compare_las"}.issubset(action_ids)
    depth_repair = next(action for action in actions if action.action_id == "depth_repair")
    assert depth_repair.creates_copy is True
    assert depth_repair.requires_confirmation is True


def test_operation_journal_and_undo_redo_foundation():
    entry = build_operation_entry(
        operation_type="depth_repair",
        title="Исправление направления глубины",
        source_object_id="las:w1:l1",
        result_object_id="las:w1:l1_repaired",
        status=OperationStatus.COMPLETED,
        creates_copy=True,
        can_undo=True,
        summary="Убывающая глубина отсортирована по возрастанию, значения кривых остались на исходных глубинах.",
    )

    rows = operation_journal_rows([entry])
    state = undo_redo_state([entry])
    assert rows[0]["operation_type"] == "depth_repair"
    assert rows[0]["creates_copy"] is True
    assert state.can_undo is True
    assert state.undo_label == "Исправление направления глубины"
