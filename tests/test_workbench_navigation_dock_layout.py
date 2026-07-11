from core.workbench_shell import (
    WORKBENCH_DOCK_LAYOUT_KEY,
    WORKBENCH_NAVIGATION_KEY,
    WorkbenchDockPane,
    WorkbenchNavigationItem,
    WorkbenchShellBuilder,
)


def test_workbench_shell_contains_default_navigation_and_dock_layout():
    model = WorkbenchShellBuilder({}).build()

    assert model.navigation_ids() == (
        "nav.dashboard",
        "nav.las_workspace",
        "nav.interpretation",
        "nav.reports",
        "nav.exports",
        "nav.documentation",
    )
    assert model.dock_layout.pane_ids()

    payload = model.to_dict()

    assert payload["navigation"][0]["workspace"] == "dashboard"
    assert "left" in payload["dock_layout"]["regions"]
    assert "center" in payload["dock_layout"]["regions"]
    assert "dock.workspace_area" in payload["dock_layout"]["regions"]["center"]


def test_workbench_navigation_can_be_overridden_from_state():
    state = {
        WORKBENCH_NAVIGATION_KEY: [
            {
                "id": "nav.custom_reports",
                "title": "Custom Reports",
                "workspace": "reports",
                "group": "output",
                "order": 5,
            }
        ]
    }

    model = WorkbenchShellBuilder(state).build()

    assert model.navigation_ids() == ("nav.custom_reports",)
    assert model.to_dict()["navigation"][0]["title"] == "Custom Reports"


def test_workbench_dock_layout_can_be_overridden_from_state():
    state = {
        WORKBENCH_DOCK_LAYOUT_KEY: [
            {
                "id": "dock.workspace_area",
                "panel_id": "workspace_area",
                "region": "center",
                "title": "Workspace Area",
                "order": 10,
            },
            {
                "id": "dock.properties",
                "panel_id": "properties",
                "region": "right",
                "title": "Properties",
                "order": 20,
                "size": 360,
                "collapsed": True,
            },
        ]
    }

    model = WorkbenchShellBuilder(state).build()
    payload = model.to_dict()["dock_layout"]

    assert model.dock_layout.pane_ids() == ("dock.workspace_area", "dock.properties")
    assert payload["regions"]["center"] == ["dock.workspace_area"]
    assert payload["regions"]["right"] == []
    assert payload["panes"][1]["size"] == 360


def test_workbench_navigation_and_dock_items_validate_required_identity():
    try:
        WorkbenchNavigationItem("", "Reports", "reports").normalized()
        assert False, "empty navigation id should fail"
    except ValueError as exc:
        assert "id" in str(exc)

    try:
        WorkbenchDockPane("dock.bad", "", "left").normalized()
        assert False, "empty dock panel id should fail"
    except ValueError as exc:
        assert "panel id" in str(exc)
