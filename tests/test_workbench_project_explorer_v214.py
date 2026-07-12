from core.workbench_project_explorer import (
    explorer_kind_icon,
    explorer_status_marker,
    filter_project_explorer_nodes,
    visible_project_explorer_nodes,
)


def _nodes():
    return (
        {"id": "project:default", "parent_id": "", "title": "Default", "kind": "project", "level": 0, "has_children": True},
        {"id": "folder:wells", "parent_id": "project:default", "title": "Wells", "kind": "folder", "level": 1, "has_children": True},
        {"id": "well:alpha", "parent_id": "folder:wells", "title": "Alpha", "kind": "well", "level": 2, "has_children": True},
        {"id": "las:one", "parent_id": "well:alpha", "title": "alpha.las", "kind": "las_version", "level": 3, "status": "ready"},
        {"id": "folder:calculations", "parent_id": "project:default", "title": "Calculations", "kind": "folder", "level": 1, "has_children": True},
        {"id": "calculation:bad", "parent_id": "folder:calculations", "title": "Run 1", "kind": "calculation", "level": 2, "metadata": {"warnings_count": 3}},
    )


def test_search_keeps_matching_node_and_all_ancestors():
    view = filter_project_explorer_nodes(_nodes(), "alpha.las")
    assert [node["id"] for node in view.nodes] == [
        "project:default", "folder:wells", "well:alpha", "las:one"
    ]
    assert view.matched_nodes == 1


def test_expansion_hides_descendants_of_closed_folder():
    visible = visible_project_explorer_nodes(_nodes(), {"project:default"})
    assert [node["id"] for node in visible] == [
        "project:default", "folder:wells", "folder:calculations"
    ]


def test_force_expand_shows_filtered_descendants():
    view = filter_project_explorer_nodes(_nodes(), "alpha")
    visible = visible_project_explorer_nodes(view.nodes, set(), force_expand=True)
    assert "well:alpha" in {node["id"] for node in visible}


def test_status_markers_are_non_alarmist_and_warning_aware():
    assert explorer_status_marker({"kind": "empty", "status": "пока нет данных"}) == "⚪"
    assert explorer_status_marker({"kind": "calculation", "metadata": {"warnings_count": 2}}) == "🟡"
    assert explorer_status_marker({"kind": "well", "status": "ready"}) == "🟢"
    assert explorer_kind_icon("calculation") == "∑"
