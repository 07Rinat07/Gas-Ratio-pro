from __future__ import annotations

import json

from services.las_viewer_recent_sessions import LasViewerRecentSessions
from services.las_viewer_session import LasViewerSession
from services.las_viewer_workspace_autosave_repository import LasViewerWorkspaceAutosaveRepository
from services.las_viewer_workspace_session_switcher import LasViewerWorkspaceSessionSwitcher


def _session(las_id: str, project_id: str = "project-1") -> LasViewerSession:
    return LasViewerSession({
        "project_id": project_id,
        "las_id": las_id,
        "depth_unit": "M",
        "depth_range": {"start": 1000.0, "stop": 1200.0},
        "tracks": [{"id": "gamma"}],
        "curves": [{"mnemonic": "GR", "track_id": "gamma"}],
        "visible_tracks": ["gamma"],
    })


def test_recent_sessions_returns_valid_metadata(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las"))
    recent = LasViewerRecentSessions(repository).list()

    assert len(recent) == 1
    assert recent[0].project_id == "project-1"
    assert recent[0].las_id == "a.las"
    assert recent[0].valid is True
    assert len(recent[0].session_key) == 20


def test_recent_sessions_marks_active_identity(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("active.las"))

    recent = LasViewerRecentSessions(repository).list(
        active_project_id="project-1",
        active_las_id="active.las",
    )

    assert recent[0].active is True


def test_recent_sessions_limit_is_enforced(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las"))
    repository.save(_session("b.las"))

    assert len(LasViewerRecentSessions(repository).list(limit=1)) == 1


def test_recent_sessions_rejects_invalid_limit(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)

    try:
        LasViewerRecentSessions(repository).list(limit=0)
    except ValueError as exc:
        assert "limit" in str(exc)
    else:
        raise AssertionError("ValueError expected")


def test_latest_filters_by_las_identity(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las"))
    repository.save(_session("b.las"))

    latest = LasViewerRecentSessions(repository).latest(las_id="a.las")

    assert latest is not None and latest.las_id == "a.las"


def test_snapshot_is_renderer_neutral(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las"))

    snapshot = LasViewerRecentSessions(repository).snapshot()

    assert snapshot["schema"] == "las.viewer.recent-sessions"
    assert snapshot["renderer_neutral"] is True
    assert snapshot["count"] == 1


def test_repository_recovers_selected_entry(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("selected.las"))
    filename = repository.entries()[0].filename

    recovery = repository.recover_entry(filename)

    assert recovery.recovered is True
    assert recovery.state is not None and recovery.state.las_id == "selected.las"


def test_repository_rejects_unsafe_selected_entry(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)

    recovery = repository.recover_entry("../outside.autosave.json")

    assert recovery.recovered is False
    assert recovery.reason == "invalid_repository_filename"


def test_switcher_activates_selected_recent_entry(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("saved.las"))
    filename = repository.entries()[0].filename
    switcher = LasViewerWorkspaceSessionSwitcher(repository, active_session=_session("current.las"))

    result = switcher.recover_entry_and_activate(filename)

    assert result.switched is True
    assert result.recovered is True
    assert switcher.active_state is not None and switcher.active_state.las_id == "saved.las"


def test_repository_removes_selected_entry_and_backup(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    session = _session("remove.las")
    repository.save(session)
    repository.save(LasViewerSession({
        "project_id": "project-1",
        "las_id": "remove.las",
        "depth_unit": "M",
        "depth_range": {"start": 1001.0, "stop": 1201.0},
        "tracks": [{"id": "gamma"}],
        "curves": [{"mnemonic": "GR", "track_id": "gamma"}],
        "visible_tracks": ["gamma"],
    }))
    filename = repository.entries()[0].filename

    result = repository.remove_entry(filename)

    assert result.removed is True
    assert result.removed_files == 2
    assert repository.entries() == ()


def test_repository_rejects_unsafe_removal(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)

    result = repository.remove_entry("../outside.autosave.json")

    assert result.removed is False
    assert result.reason == "invalid_repository_filename"


def test_recent_sessions_removes_by_public_session_key(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("remove-key.las"))
    recent_service = LasViewerRecentSessions(repository)
    item = recent_service.list()[0]

    result = recent_service.remove(item.session_key)

    assert result.removed is True
    assert result.session_key == item.session_key
    assert recent_service.list() == ()
    assert result.to_dict()["renderer_neutral"] is True


def test_recent_sessions_missing_key_does_not_delete_anything(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("keep.las"))
    recent_service = LasViewerRecentSessions(repository)

    result = recent_service.remove("unknown-key")

    assert result.removed is False
    assert result.reason == "missing_recent_session"
    assert len(recent_service.list()) == 1


def test_recent_sessions_can_pin_and_sort_items_first(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("older.las"))
    repository.save(_session("newer.las"))
    service = LasViewerRecentSessions(repository)
    older = next(item for item in service.list() if item.las_id == "older.las")

    result = service.pin(older.session_key)
    items = service.list()

    assert result.changed is True
    assert items[0].las_id == "older.las"
    assert items[0].pinned is True


def test_recent_session_pin_is_persistent(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("pinned.las"))
    first = LasViewerRecentSessions(repository)
    item = first.list()[0]
    first.pin(item.session_key)

    restored = LasViewerRecentSessions(repository).list()[0]

    assert restored.pinned is True


def test_recent_session_can_be_unpinned(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("pinned.las"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]
    service.pin(item.session_key)

    result = service.pin(item.session_key, pinned=False)

    assert result.changed is True
    assert service.list()[0].pinned is False


def test_removing_recent_session_cleans_pin_metadata(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("remove-pinned.las"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]
    service.pin(item.session_key)

    service.remove(item.session_key)
    repository.save(_session("remove-pinned.las"))

    assert service.list()[0].pinned is False


def test_snapshot_reports_pinned_count(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("pinned.las"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]
    service.pin(item.session_key)

    snapshot = service.snapshot()

    assert snapshot["version"] == "1.3"
    assert snapshot["pinned_count"] == 1
    assert snapshot["items"][0]["pinned"] is True


def test_recent_sessions_searches_case_insensitively(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("Gamma_Main.LAS", project_id="North-Field"))
    repository.save(_session("density.las", project_id="South-Field"))

    items = LasViewerRecentSessions(repository).list(query="gamma_main")

    assert [item.las_id for item in items] == ["Gamma_Main.LAS"]


def test_recent_sessions_filters_by_project_and_las_id(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las", project_id="project-a"))
    repository.save(_session("b.las", project_id="project-b"))
    service = LasViewerRecentSessions(repository)

    by_project = service.list(project_id="project-b")
    by_las = service.list(las_id="a.las")

    assert [item.las_id for item in by_project] == ["b.las"]
    assert [item.project_id for item in by_las] == ["project-a"]


def test_recent_sessions_filters_pinned_only(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("pinned.las"))
    repository.save(_session("regular.las"))
    service = LasViewerRecentSessions(repository)
    pinned = next(item for item in service.list() if item.las_id == "pinned.las")
    service.pin(pinned.session_key)

    items = service.list(pinned_only=True)

    assert [item.las_id for item in items] == ["pinned.las"]


def test_recent_sessions_filters_active_only(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("active.las"))
    repository.save(_session("other.las"))

    items = LasViewerRecentSessions(repository).list(
        active_project_id="project-1",
        active_las_id="active.las",
        active_only=True,
    )

    assert [item.las_id for item in items] == ["active.las"]


def test_recent_sessions_snapshot_reports_filters(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las"))

    snapshot = LasViewerRecentSessions(repository).snapshot(query="a", pinned_only=True)

    assert snapshot["version"] == "1.3"
    assert snapshot["filters"]["query"] == "a"
    assert snapshot["filters"]["pinned_only"] is True


def test_recent_sessions_sorts_by_filename_ascending(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("zeta.las"))
    repository.save(_session("Alpha.las"))

    items = LasViewerRecentSessions(repository).list(
        sort_by="filename",
        sort_order="asc",
    )

    assert [item.las_id for item in items] == ["Alpha.las", "zeta.las"]


def test_recent_sessions_sorts_by_project_descending(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las", project_id="Alpha"))
    repository.save(_session("b.las", project_id="Zulu"))

    items = LasViewerRecentSessions(repository).list(
        sort_by="project",
        sort_order="desc",
    )

    assert [item.project_id for item in items] == ["Zulu", "Alpha"]


def test_recent_sessions_can_disable_pinned_first(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("zeta.las"))
    repository.save(_session("alpha.las"))
    service = LasViewerRecentSessions(repository)
    zeta = next(item for item in service.list() if item.las_id == "zeta.las")
    service.pin(zeta.session_key)

    items = service.list(
        sort_by="filename",
        sort_order="asc",
        pinned_first=False,
    )

    assert [item.las_id for item in items] == ["alpha.las", "zeta.las"]


def test_recent_sessions_rejects_invalid_sort_options(tmp_path):
    service = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path))

    for kwargs in ({"sort_by": "unknown"}, {"sort_order": "sideways"}):
        try:
            service.list(**kwargs)
        except ValueError as exc:
            assert "sort" in str(exc)
        else:
            raise AssertionError("ValueError expected")


def test_recent_sessions_snapshot_reports_sorting(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las"))

    snapshot = LasViewerRecentSessions(repository).snapshot(
        sort_by="filename",
        sort_order="asc",
        pinned_first=False,
    )

    assert snapshot["version"] == "1.3"
    assert snapshot["sorting"] == {
        "sort_by": "filename",
        "sort_order": "asc",
        "pinned_first": False,
    }


def test_recent_sessions_paginates_sorted_results(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    for name in ("delta.las", "alpha.las", "charlie.las", "bravo.las", "echo.las"):
        repository.save(_session(name))

    page = LasViewerRecentSessions(repository).paginate(
        page=2,
        page_size=2,
        sort_by="filename",
        sort_order="asc",
    )

    assert [item.las_id for item in page.items] == ["charlie.las", "delta.las"]
    assert page.total_count == 5
    assert page.page_count == 3
    assert page.has_previous is True
    assert page.has_next is True
    assert page.start_index == 3
    assert page.end_index == 4


def test_recent_sessions_pagination_handles_empty_out_of_range_page(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("only.las"))

    page = LasViewerRecentSessions(repository).paginate(page=3, page_size=2)

    assert page.items == ()
    assert page.total_count == 1
    assert page.page_count == 1
    assert page.has_previous is True
    assert page.has_next is False
    assert page.start_index == 0
    assert page.end_index == 0


def test_recent_sessions_pagination_applies_filters_before_counting(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las", project_id="north"))
    repository.save(_session("b.las", project_id="south"))
    repository.save(_session("c.las", project_id="north"))

    page = LasViewerRecentSessions(repository).paginate(
        page=1,
        page_size=1,
        project_id="north",
        sort_by="filename",
        sort_order="asc",
    )

    assert [item.las_id for item in page.items] == ["a.las"]
    assert page.total_count == 2
    assert page.page_count == 2
    assert page.has_next is True


def test_recent_sessions_pagination_contract_is_renderer_neutral(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las"))

    payload = LasViewerRecentSessions(repository).paginate(page=1, page_size=10).to_dict()

    assert payload["schema"] == "las.viewer.recent-session-page"
    assert payload["version"] == "1.0"
    assert payload["renderer_neutral"] is True
    assert payload["total_count"] == 1
    assert payload["items"][0]["las_id"] == "a.las"


def test_recent_sessions_pagination_rejects_invalid_parameters(tmp_path):
    service = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path))

    for kwargs in ({"page": 0}, {"page_size": 0}):
        try:
            service.paginate(**kwargs)
        except ValueError as exc:
            assert "page" in str(exc)
        else:
            raise AssertionError("ValueError expected")


def test_recent_sessions_groups_by_project_preserving_item_order(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("b.las", project_id="north"))
    repository.save(_session("a.las", project_id="south"))
    repository.save(_session("c.las", project_id="north"))

    groups = LasViewerRecentSessions(repository).group(
        group_by="project", sort_by="filename", sort_order="asc"
    )

    assert [group.key for group in groups] == ["south", "north"]
    assert [item.las_id for item in groups[1].items] == ["b.las", "c.las"]


def test_recent_sessions_groups_by_status(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("active.las", project_id="p"))
    repository.save(_session("pinned.las", project_id="p"))
    service = LasViewerRecentSessions(repository)
    pinned = next(item for item in service.list(limit=10) if item.las_id == "pinned.las")
    service.pin(pinned.session_key)

    groups = service.group(group_by="status", active_project_id="p", active_las_id="active.las")

    assert {group.key for group in groups} == {"active", "pinned"}


def test_recent_session_group_contract_is_renderer_neutral(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las", project_id="north"))

    payload = LasViewerRecentSessions(repository).group()[0].to_dict()

    assert payload["schema"] == "las.viewer.recent-session-group"
    assert payload["version"] == "1.0"
    assert payload["count"] == 1
    assert payload["renderer_neutral"] is True


def test_recent_sessions_group_applies_filters(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las", project_id="north"))
    repository.save(_session("b.las", project_id="south"))

    groups = LasViewerRecentSessions(repository).group(project_id="north")

    assert len(groups) == 1
    assert groups[0].key == "north"


def test_recent_sessions_group_rejects_invalid_mode(tmp_path):
    service = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path))

    try:
        service.group(group_by="unsupported")
    except ValueError as exc:
        assert "group_by" in str(exc)
    else:
        raise AssertionError("ValueError expected")


def test_recent_session_group_pagination_slices_groups_after_grouping(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las", project_id="alpha"))
    repository.save(_session("b.las", project_id="beta"))
    repository.save(_session("c.las", project_id="gamma"))
    service = LasViewerRecentSessions(repository)

    page = service.paginate_groups(
        group_by="project",
        page=2,
        page_size=2,
        sort_by="filename",
        sort_order="asc",
    )

    assert [group.key for group in page.groups] == ["gamma"]
    assert page.total_group_count == 3
    assert page.total_item_count == 3
    assert page.page_count == 2
    assert page.has_previous is True
    assert page.has_next is False
    assert page.start_index == 3
    assert page.end_index == 3


def test_recent_session_group_pagination_preserves_group_items(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las", project_id="north"))
    repository.save(_session("b.las", project_id="north"))
    repository.save(_session("c.las", project_id="south"))

    page = LasViewerRecentSessions(repository).paginate_groups(
        group_by="project",
        page=1,
        page_size=1,
        sort_by="filename",
        sort_order="asc",
    )

    assert len(page.groups) == 1
    assert page.groups[0].key == "north"
    assert [item.las_id for item in page.groups[0].items] == ["a.las", "b.las"]
    assert page.total_item_count == 3


def test_recent_session_group_page_contract_is_renderer_neutral(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las", project_id="north"))

    payload = LasViewerRecentSessions(repository).paginate_groups().to_dict()

    assert payload["schema"] == "las.viewer.recent-session-group-page"
    assert payload["version"] == "1.0"
    assert payload["renderer_neutral"] is True
    assert payload["total_group_count"] == 1
    assert payload["total_item_count"] == 1
    assert payload["groups"][0]["key"] == "north"


def test_recent_session_group_pagination_rejects_invalid_parameters(tmp_path):
    service = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path))

    for kwargs in ({"page": 0}, {"page_size": 0}):
        try:
            service.paginate_groups(**kwargs)
        except ValueError as exc:
            assert "page" in str(exc)
        else:
            raise AssertionError("ValueError expected")


def test_recent_session_group_can_be_collapsed(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las", project_id="project-a"))
    service = LasViewerRecentSessions(repository)

    changed = service.set_group_collapsed("project", "project-a")
    group = service.group(group_by="project")[0]

    assert changed is True
    assert group.collapsed is True
    assert group.to_dict()["expanded"] is False


def test_recent_session_group_collapse_state_is_persistent(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las", project_id="project-a"))
    LasViewerRecentSessions(repository).set_group_collapsed("project", "project-a")

    group = LasViewerRecentSessions(repository).group(group_by="project")[0]

    assert group.collapsed is True


def test_recent_session_group_can_be_expanded_again(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las", project_id="project-a"))
    service = LasViewerRecentSessions(repository)
    service.set_group_collapsed("project", "project-a")

    changed = service.set_group_collapsed("project", "project-a", collapsed=False)

    assert changed is True
    assert service.group(group_by="project")[0].collapsed is False


def test_recent_session_group_toggle_returns_new_state(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las", project_id="project-a"))
    service = LasViewerRecentSessions(repository)

    assert service.toggle_group_collapsed("project", "project-a") is True
    assert service.toggle_group_collapsed("project", "project-a") is False


def test_recent_session_group_preferences_preserve_pinned_sessions(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las", project_id="project-a"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]
    service.pin(item.session_key)

    service.set_group_collapsed("project", "project-a")

    assert service.list()[0].pinned is True
    assert service.group(group_by="project")[0].collapsed is True


def test_recent_session_navigation_state_is_persistent(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las", project_id="project-a"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]

    saved = service.set_navigation_state(
        group_by="project",
        selected_group_key="project-a",
        selected_session_key=item.session_key,
        page=3,
    )
    restored = LasViewerRecentSessions(repository).navigation_state()

    assert restored == saved
    assert restored.to_dict()["renderer_neutral"] is True


def test_recent_session_navigation_state_survives_pin_and_collapse_updates(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las", project_id="project-a"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]
    service.set_navigation_state(
        group_by="project",
        selected_group_key="project-a",
        selected_session_key=item.session_key,
        page=2,
    )

    service.pin(item.session_key)
    service.set_group_collapsed("project", "project-a")

    state = service.navigation_state()
    assert state.selected_group_key == "project-a"
    assert state.selected_session_key == item.session_key
    assert state.page == 2


def test_recent_session_navigation_state_rejects_invalid_parameters(tmp_path):
    service = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path))

    for kwargs in ({"group_by": "bad"}, {"group_by": "project", "page": 0}):
        try:
            service.set_navigation_state(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("ValueError expected")


def test_recent_session_locate_resolves_group_page_and_item_position(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las", project_id="project-a"))
    repository.save(_session("b.las", project_id="project-b"))
    repository.save(_session("c.las", project_id="project-c"))
    service = LasViewerRecentSessions(repository)
    target_item = next(item for item in service.list(limit=10) if item.project_id == "project-a")

    target = service.locate_session(
        target_item.session_key,
        group_by="project",
        page_size=2,
        persist=True,
    )

    assert target.found is True
    assert target.group_key == "project-a"
    assert target.page >= 1
    assert target.item_index == 0
    assert service.navigation_state().selected_session_key == target_item.session_key
    assert target.to_dict()["renderer_neutral"] is True


def test_recent_session_locate_reports_missing_session(tmp_path):
    service = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path))

    target = service.locate_session("missing", group_by="project", page_size=2)

    assert target.found is False
    assert target.reason == "missing_recent_session"


def test_recent_session_focus_latest_persists_navigation(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las", project_id="project-a"))
    repository.save(_session("b.las", project_id="project-b"))
    service = LasViewerRecentSessions(repository)

    target = service.focus_latest(group_by="project", page_size=1)
    state = service.navigation_state()

    assert target.found is True
    assert state.selected_session_key == target.session_key
    assert state.selected_group_key == target.group_key
    assert state.page == target.page


def test_recent_session_locate_validates_group_and_page_size(tmp_path):
    service = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path))

    for kwargs in ({"group_by": "bad"}, {"page_size": 0}):
        try:
            service.locate_session("session", **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("ValueError expected")


def test_recent_session_navigation_history_supports_back_and_forward(tmp_path):
    service = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path))
    first = service.set_navigation_state(group_by="project", selected_group_key="a", page=1)
    second = service.set_navigation_state(group_by="project", selected_group_key="b", page=2)

    assert service.navigation_history().can_go_back is True
    assert service.navigate_back() == first
    assert service.navigation_state() == first
    assert service.navigate_forward() == second
    assert service.navigation_state() == second


def test_recent_session_navigation_history_discards_forward_branch(tmp_path):
    service = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path))
    service.set_navigation_state(group_by="project", selected_group_key="a", page=1)
    service.set_navigation_state(group_by="project", selected_group_key="b", page=2)
    service.navigate_back()

    third = service.set_navigation_state(group_by="las_id", selected_group_key="c", page=3)
    history = service.navigation_history()

    assert history.current == third
    assert history.can_go_forward is False
    assert [entry.selected_group_key for entry in history.entries] == ["a", "c"]


def test_recent_session_navigation_history_ignores_duplicate_state(tmp_path):
    service = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path))
    service.set_navigation_state(group_by="project", selected_group_key="a", page=1)
    service.set_navigation_state(group_by="project", selected_group_key="a", page=1)

    assert len(service.navigation_history().entries) == 1


def test_recent_session_navigation_history_is_persistent(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    service = LasViewerRecentSessions(repository)
    service.set_navigation_state(group_by="project", selected_group_key="a", page=1)
    service.set_navigation_state(group_by="las_id", selected_group_key="b", page=2)

    restored = LasViewerRecentSessions(repository).navigation_history()

    assert restored.index == 1
    assert restored.current is not None
    assert restored.current.selected_group_key == "b"
    assert restored.to_dict()["renderer_neutral"] is True


def test_recent_session_bookmark_is_persistent_and_renderer_neutral(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("bookmark.las"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]

    result = service.set_bookmark(item.session_key, label="Primary log")
    restored = LasViewerRecentSessions(repository).bookmarks()

    assert result.changed is True
    assert restored[0].label == "Primary log"
    assert restored[0].to_dict()["renderer_neutral"] is True


def test_recent_session_bookmark_uses_las_id_as_default_label(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("default-label.las"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]

    result = service.set_bookmark(item.session_key)

    assert result.label == "default-label.las"


def test_recent_session_bookmark_can_be_removed(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("remove-bookmark.las"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]
    service.set_bookmark(item.session_key, label="Temporary")

    result = service.remove_bookmark(item.session_key)

    assert result.changed is True
    assert service.bookmarks() == ()


def test_recent_session_focus_bookmark_persists_navigation(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("focus-bookmark.las", project_id="north"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]
    service.set_bookmark(item.session_key, label="North")

    target = service.focus_bookmark(item.session_key, group_by="project", page_size=1)

    assert target.found is True
    assert service.navigation_state().selected_session_key == item.session_key


def test_removing_recent_session_cleans_bookmark_metadata(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("clean-bookmark.las"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]
    service.set_bookmark(item.session_key, label="Clean")

    service.remove(item.session_key)
    repository.save(_session("clean-bookmark.las"))

    assert service.bookmarks() == ()


def test_recent_session_bookmarks_support_folders(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("gamma.las"))
    repository.save(_session("density.las"))
    service = LasViewerRecentSessions(repository)
    items = {item.las_id: item for item in service.list(limit=10)}

    service.set_bookmark(items["gamma.las"].session_key, label="Gamma", folder="Primary")
    service.set_bookmark(items["density.las"].session_key, label="Density", folder="Secondary")

    assert [item.label for item in service.bookmarks(folder="Primary")] == ["Gamma"]
    assert service.bookmark_folders() == ("Primary", "Secondary")


def test_recent_session_bookmarks_sort_by_manual_position(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("a.las"))
    repository.save(_session("b.las"))
    service = LasViewerRecentSessions(repository)
    items = {item.las_id: item for item in service.list(limit=10)}

    service.set_bookmark(items["a.las"].session_key, label="A", position=20)
    service.set_bookmark(items["b.las"].session_key, label="B", position=10)

    assert [item.label for item in service.bookmarks()] == ["B", "A"]


def test_recent_session_bookmarks_sort_by_label_descending(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("alpha.las"))
    repository.save(_session("zeta.las"))
    service = LasViewerRecentSessions(repository)
    items = {item.las_id: item for item in service.list(limit=10)}

    service.set_bookmark(items["alpha.las"].session_key, label="Alpha")
    service.set_bookmark(items["zeta.las"].session_key, label="Zeta")

    assert [item.label for item in service.bookmarks(sort_by="label", sort_order="desc")] == ["Zeta", "Alpha"]


def test_recent_session_bookmark_folder_and_position_are_persistent(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("persist-folder.las"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]
    service.set_bookmark(item.session_key, label="Persistent", folder="Field A", position=7)

    restored = LasViewerRecentSessions(repository).bookmarks()[0]

    assert restored.folder == "Field A"
    assert restored.position == 7
    assert restored.to_dict()["version"] == "1.1"


def test_recent_session_bookmarks_reject_invalid_sort_options(tmp_path):
    service = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path))

    for kwargs in ({"sort_by": "unknown"}, {"sort_order": "sideways"}):
        try:
            service.bookmarks(**kwargs)
        except ValueError as exc:
            assert "sort" in str(exc)
        else:
            raise AssertionError("ValueError expected")


def test_recent_session_bookmarks_export_and_import_between_workspaces(tmp_path):
    source_repository = LasViewerWorkspaceAutosaveRepository(tmp_path / "source")
    source_repository.save(_session("portable.las", project_id="field-a"))
    source = LasViewerRecentSessions(source_repository)
    source_item = source.list()[0]
    source.set_bookmark(source_item.session_key, label="Portable", folder="Favorites", position=3)
    export_path = tmp_path / "bookmarks.json"

    payload = source.export_bookmarks(export_path)

    target_repository = LasViewerWorkspaceAutosaveRepository(tmp_path / "target")
    target_repository.save(_session("portable.las", project_id="field-a"))
    target = LasViewerRecentSessions(target_repository)
    result = target.import_bookmarks(export_path)
    imported = target.bookmarks()[0]

    assert payload["schema"] == "las.viewer.recent-session-bookmark-exchange"
    assert result.imported == 1
    assert imported.label == "Portable"
    assert imported.folder == "Favorites"
    assert imported.position == 3


def test_recent_session_bookmark_import_supports_conflict_policies(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("conflict.las"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]
    service.set_bookmark(item.session_key, label="Existing")
    payload = service.export_bookmarks()
    payload["bookmarks"][0]["label"] = "Imported"

    skipped = service.import_bookmarks(payload, conflict="skip")
    overwritten = service.import_bookmarks(payload, conflict="overwrite")

    assert skipped.conflicts == 1
    assert skipped.skipped == 1
    assert overwritten.imported == 1
    assert service.bookmarks()[0].label == "Imported"


def test_recent_session_bookmark_import_is_transactional_on_conflict_error(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("transaction.las"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]
    service.set_bookmark(item.session_key, label="Original")
    payload = service.export_bookmarks()
    payload["bookmarks"][0]["label"] = "Replacement"

    try:
        service.import_bookmarks(payload, conflict="error")
    except ValueError as exc:
        assert "conflict" in str(exc)
    else:
        raise AssertionError("ValueError expected")

    assert service.bookmarks()[0].label == "Original"


def test_recent_session_bookmark_import_reports_missing_sessions(tmp_path):
    service = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path))
    payload = {
        "schema": "las.viewer.recent-session-bookmark-exchange",
        "version": "1.0",
        "renderer_neutral": True,
        "bookmarks": [{"session_key": "missing", "label": "Missing"}],
    }

    result = service.import_bookmarks(payload)

    assert result.missing_sessions == 1
    assert service.bookmarks() == ()


def test_bookmark_exchange_migrates_legacy_contract_without_mutation():
    legacy = {
        "schema": "las.viewer.recent-session-bookmark-exchange",
        "version": "0.9",
        "renderer_neutral": True,
        "items": [{"key": "abc", "name": "Gamma", "group": "Primary", "order": 4}],
    }

    migrated = LasViewerRecentSessions.migrate_bookmark_exchange(legacy)

    assert legacy["version"] == "0.9"
    assert migrated["version"] == "1.0"
    assert migrated["bookmarks"][0]["session_key"] == "abc"
    assert migrated["bookmarks"][0]["label"] == "Gamma"
    assert migrated["bookmarks"][0]["folder"] == "Primary"
    assert migrated["bookmarks"][0]["position"] == 4


def test_bookmark_exchange_validation_rejects_missing_identity():
    payload = {
        "schema": "las.viewer.recent-session-bookmark-exchange",
        "version": "1.0",
        "renderer_neutral": True,
        "bookmarks": [{"label": "Broken", "position": 0}],
    }

    try:
        LasViewerRecentSessions.validate_bookmark_exchange(payload)
    except ValueError as exc:
        assert "identity" in str(exc)
    else:
        raise AssertionError("ValueError expected")


def test_bookmark_exchange_validation_reports_label_fallback():
    payload = {
        "schema": "las.viewer.recent-session-bookmark-exchange",
        "version": "1.0",
        "renderer_neutral": True,
        "bookmarks": [{"session_key": "abc", "label": "", "position": 0}],
    }

    assert LasViewerRecentSessions.validate_bookmark_exchange(payload) == ("bookmark_label_fallback:0",)


def test_recent_session_bookmark_import_accepts_legacy_contract(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("legacy-bookmark.las"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]
    payload = {
        "schema": "las.viewer.recent-session-bookmark-exchange",
        "version": "0.9",
        "renderer_neutral": True,
        "items": [{"key": item.session_key, "name": "Legacy", "group": "Migrated", "order": 2}],
    }

    result = service.import_bookmarks(payload)

    assert result.imported == 1
    bookmark = service.bookmarks()[0]
    assert (bookmark.label, bookmark.folder, bookmark.position) == ("Legacy", "Migrated", 2)


def test_recent_session_bookmarks_backup_and_restore(tmp_path):
    source_repository = LasViewerWorkspaceAutosaveRepository(tmp_path / "source")
    source_repository.save(_session("backup.las", project_id="field-a"))
    source = LasViewerRecentSessions(source_repository)
    source_item = source.list()[0]
    source.set_bookmark(source_item.session_key, label="Backup", folder="Primary", position=2)
    backup_path = tmp_path / "bookmarks-backup.zip"

    manifest = source.backup_bookmarks(backup_path)

    target_repository = LasViewerWorkspaceAutosaveRepository(tmp_path / "target")
    target_repository.save(_session("backup.las", project_id="field-a"))
    target = LasViewerRecentSessions(target_repository)
    result = target.restore_bookmark_backup(backup_path)

    assert manifest["schema"] == "las.viewer.recent-session-bookmark-backup"
    assert result.imported == 1
    assert target.bookmarks()[0].label == "Backup"


def test_recent_session_bookmark_backup_rejects_checksum_mismatch(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("tampered.las"))
    service = LasViewerRecentSessions(repository)
    service.set_bookmark(service.list()[0].session_key, label="Tampered")
    backup_path = tmp_path / "tampered.zip"
    service.backup_bookmarks(backup_path)

    from zipfile import ZIP_DEFLATED, ZipFile
    with ZipFile(backup_path, "r") as archive:
        manifest = archive.read("manifest.json")
    with ZipFile(backup_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", manifest)
        archive.writestr("bookmarks.json", b'{}')

    try:
        service.restore_bookmark_backup(backup_path)
    except ValueError as exc:
        assert "checksum" in str(exc)
    else:
        raise AssertionError("ValueError expected")


def test_recent_session_bookmark_backup_rejects_unexpected_members(tmp_path):
    from zipfile import ZipFile
    backup_path = tmp_path / "unsafe.zip"
    with ZipFile(backup_path, "w") as archive:
        archive.writestr("manifest.json", "{}")
        archive.writestr("bookmarks.json", "{}")
        archive.writestr("../outside.txt", "unsafe")

    service = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path / "repo"))
    try:
        service.restore_bookmark_backup(backup_path)
    except ValueError as exc:
        assert "contents" in str(exc)
    else:
        raise AssertionError("ValueError expected")


def test_removed_bookmark_moves_to_recoverable_trash(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("trash-bookmark.las"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]
    service.set_bookmark(item.session_key, label="Recoverable", folder="Primary", position=3)

    result = service.remove_bookmark(item.session_key)
    trash = service.bookmark_trash()

    assert result.changed is True
    assert service.bookmarks() == ()
    assert len(trash) == 1
    assert trash[0].session_key == item.session_key
    assert (trash[0].label, trash[0].folder, trash[0].position) == ("Recoverable", "Primary", 3)
    assert trash[0].to_dict()["renderer_neutral"] is True


def test_bookmark_can_be_restored_from_trash(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("restore-trash.las"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]
    service.set_bookmark(item.session_key, label="Restore", folder="Pinned", position=2)
    service.remove_bookmark(item.session_key)

    result = LasViewerRecentSessions(repository).restore_bookmark(item.session_key)
    bookmarks = service.bookmarks()

    assert result.changed is True
    assert result.reason == "restored"
    assert len(bookmarks) == 1
    assert (bookmarks[0].label, bookmarks[0].folder, bookmarks[0].position) == ("Restore", "Pinned", 2)
    assert service.bookmark_trash() == ()


def test_bookmark_restore_fails_when_recent_session_no_longer_exists(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("missing-session.las"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]
    service.set_bookmark(item.session_key, label="Missing")
    service.remove_bookmark(item.session_key)
    repository.remove_entry(item.filename)

    result = service.restore_bookmark(item.session_key)

    assert result.changed is False
    assert result.reason == "missing_recent_session"
    assert len(service.bookmark_trash()) == 1


def test_bookmark_trash_supports_single_and_full_purge(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("first-trash.las"))
    repository.save(_session("second-trash.las"))
    service = LasViewerRecentSessions(repository)
    items = service.list(limit=10)
    for item in items:
        service.set_bookmark(item.session_key, label=item.filename)
        service.remove_bookmark(item.session_key)

    first_key = service.bookmark_trash()[0].session_key
    assert service.purge_bookmark_trash(first_key) == 1
    assert len(service.bookmark_trash()) == 1
    assert service.purge_bookmark_trash() == 1
    assert service.bookmark_trash() == ()


def test_bookmark_trash_records_deletion_timestamp(tmp_path, monkeypatch):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("timestamped-trash.las"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]
    service.set_bookmark(item.session_key, label="Timestamped")
    monkeypatch.setattr("services.las_viewer_recent_sessions.time.time_ns", lambda: 123456789)

    service.remove_bookmark(item.session_key)
    trash_item = service.bookmark_trash()[0]

    assert trash_item.deleted_at_ns == 123456789
    assert trash_item.to_dict()["deleted_at_ns"] == 123456789


def test_expired_bookmark_trash_is_purged_by_retention_period(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("old-trash.las"))
    repository.save(_session("fresh-trash.las"))
    service = LasViewerRecentSessions(repository)
    items = {item.las_id: item for item in service.list(limit=10)}
    service.set_bookmark(items["old-trash.las"].session_key, label="Old")
    service.set_bookmark(items["fresh-trash.las"].session_key, label="Fresh")

    import services.las_viewer_recent_sessions as module
    original = module.time.time_ns
    try:
        module.time.time_ns = lambda: 1_000_000_000_000_000
        service.remove_bookmark(items["old-trash.las"].session_key)
        module.time.time_ns = lambda: 1_000_000_000_000_000 + 5 * 86_400_000_000_000
        service.remove_bookmark(items["fresh-trash.las"].session_key)
    finally:
        module.time.time_ns = original

    removed = service.purge_expired_bookmark_trash(
        3,
        now_ns=1_000_000_000_000_000 + 6 * 86_400_000_000_000,
    )

    assert removed == 1
    assert [item.label for item in service.bookmark_trash()] == ["Fresh"]


def test_legacy_trash_without_timestamp_is_not_auto_purged(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.directory.mkdir(parents=True, exist_ok=True)
    metadata = repository.directory / LasViewerRecentSessions.METADATA_FILENAME
    metadata.write_text(
        '{"schema":"las.viewer.recent-session-preferences","version":"1.6",'
        '"bookmark_trash":{"legacy":{"label":"Legacy","deletion_order":1}},'
        '"pinned_session_keys":[],"collapsed_groups":[]}',
        encoding="utf-8",
    )
    service = LasViewerRecentSessions(repository)

    assert service.purge_expired_bookmark_trash(0, now_ns=999999999) == 0
    assert service.bookmark_trash()[0].label == "Legacy"


def test_expired_bookmark_purge_validates_retention(tmp_path):
    service = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path))
    for value in (-1, float("inf"), "invalid"):
        try:
            service.purge_expired_bookmark_trash(value)
        except ValueError:
            pass
        else:
            raise AssertionError("ValueError expected")


def test_bookmark_trash_retention_policy_persists_across_restart(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    service = LasViewerRecentSessions(repository)

    policy = service.configure_bookmark_trash_retention(14)
    restored = LasViewerRecentSessions(repository).bookmark_trash_retention()

    assert policy.enabled is True
    assert restored.enabled is True
    assert restored.retention_days == 14
    assert restored.last_cleanup_ns == 0
    assert restored.to_dict()["renderer_neutral"] is True


def test_bookmark_trash_synchronization_uses_persisted_policy(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("expired-restart-trash.las"))
    repository.save(_session("fresh-restart-trash.las"))
    service = LasViewerRecentSessions(repository)
    items = {item.las_id: item for item in service.list(limit=10)}
    service.set_bookmark(items["expired-restart-trash.las"].session_key, label="Expired")
    service.set_bookmark(items["fresh-restart-trash.las"].session_key, label="Fresh")

    import services.las_viewer_recent_sessions as module
    original = module.time.time_ns
    try:
        module.time.time_ns = lambda: 1_000_000_000_000_000
        service.remove_bookmark(items["expired-restart-trash.las"].session_key)
        module.time.time_ns = lambda: 1_000_000_000_000_000 + 9 * 86_400_000_000_000
        service.remove_bookmark(items["fresh-restart-trash.las"].session_key)
    finally:
        module.time.time_ns = original

    service.configure_bookmark_trash_retention(7)
    restarted = LasViewerRecentSessions(repository)
    now_ns = 1_000_000_000_000_000 + 10 * 86_400_000_000_000

    assert restarted.synchronize_bookmark_trash(now_ns=now_ns) == 1
    assert [item.label for item in restarted.bookmark_trash()] == ["Fresh"]
    assert restarted.bookmark_trash_retention().last_cleanup_ns == now_ns


def test_disabled_bookmark_trash_retention_does_not_purge(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("disabled-retention.las"))
    service = LasViewerRecentSessions(repository)
    item = service.list()[0]
    service.set_bookmark(item.session_key, label="Keep")
    service.remove_bookmark(item.session_key)
    service.configure_bookmark_trash_retention(None)

    assert LasViewerRecentSessions(repository).synchronize_bookmark_trash(now_ns=10**18) == 0
    assert len(service.bookmark_trash()) == 1


def test_bookmark_trash_journal_records_remove_restore_and_purge(tmp_path, monkeypatch):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("audit.las"))
    service = LasViewerRecentSessions(repository)
    key = service.list()[0].session_key
    service.set_bookmark(key, label="Audit")

    import itertools
    times = itertools.count(100, 100)
    monkeypatch.setattr("services.las_viewer_recent_sessions.time.time_ns", lambda: next(times))

    assert service.remove_bookmark(key).changed is True
    assert service.restore_bookmark(key).changed is True
    assert service.remove_bookmark(key).changed is True
    assert service.purge_bookmark_trash(key) == 1

    events = service.bookmark_trash_journal()
    assert [event.action for event in events] == ["purged", "removed", "restored", "removed"]
    assert all(event.session_key == key for event in events)
    assert events[-1].label == "Audit"
    assert events[0].to_dict()["renderer_neutral"] is True


def test_bookmark_trash_journal_persists_and_can_be_cleared(tmp_path):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("persist-audit.las"))
    service = LasViewerRecentSessions(repository)
    key = service.list()[0].session_key
    service.set_bookmark(key, label="Persistent")
    service.remove_bookmark(key)

    restarted = LasViewerRecentSessions(repository)
    assert restarted.bookmark_trash_journal()[0].action == "removed"
    assert restarted.clear_bookmark_trash_journal() == 1
    assert LasViewerRecentSessions(repository).bookmark_trash_journal() == ()


def test_bookmark_trash_journal_validates_limit(tmp_path):
    service = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path))
    try:
        service.bookmark_trash_journal(limit=0)
    except ValueError as exc:
        assert "limit" in str(exc)
    else:
        raise AssertionError("ValueError expected")


def test_bookmark_trash_journal_query_filters_events(tmp_path, monkeypatch):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("query-audit.las"))
    service = LasViewerRecentSessions(repository)
    key = service.list()[0].session_key
    service.set_bookmark(key, label="Query Label")

    import itertools
    times = itertools.count(100, 100)
    monkeypatch.setattr("services.las_viewer_recent_sessions.time.time_ns", lambda: next(times))
    service.remove_bookmark(key)
    service.restore_bookmark(key)

    removed = service.query_bookmark_trash_journal(action="removed")
    assert len(removed) == 1
    assert removed[0].label == "Query Label"
    assert service.query_bookmark_trash_journal(query="query label")[0].session_key == key
    assert service.query_bookmark_trash_journal(occurred_from_ns=150)[0].action == "restored"


def test_bookmark_trash_journal_query_validates_filters(tmp_path):
    service = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path))
    for kwargs in ({"action": "unknown"}, {"occurred_from_ns": 20, "occurred_to_ns": 10}):
        try:
            service.query_bookmark_trash_journal(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("ValueError expected")


def test_export_bookmark_trash_journal_writes_portable_json(tmp_path, monkeypatch):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path)
    repository.save(_session("export-audit.las"))
    service = LasViewerRecentSessions(repository)
    key = service.list()[0].session_key
    service.set_bookmark(key, label="Export")
    monkeypatch.setattr("services.las_viewer_recent_sessions.time.time_ns", lambda: 123456)
    service.remove_bookmark(key)

    destination = tmp_path / "exports" / "bookmark-trash-audit.json"
    payload = service.export_bookmark_trash_journal(destination, action="removed")
    loaded = json.loads(destination.read_text(encoding="utf-8"))

    assert payload["event_count"] == 1
    assert loaded["schema"] == "las.viewer.recent-session-bookmark-trash-journal-export"
    assert loaded["events"][0]["session_key"] == key
    assert len(loaded["sha256"]) == 64


def test_import_bookmark_trash_journal_restores_valid_export(tmp_path, monkeypatch):
    source_repository = LasViewerWorkspaceAutosaveRepository(tmp_path / "source")
    source_repository.save(_session("restore-audit.las"))
    source = LasViewerRecentSessions(source_repository)
    key = source.list()[0].session_key
    source.set_bookmark(key, label="Restore")
    monkeypatch.setattr("services.las_viewer_recent_sessions.time.time_ns", lambda: 987654)
    source.remove_bookmark(key)
    export_path = tmp_path / "audit.json"
    source.export_bookmark_trash_journal(export_path)

    target = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path / "target"))
    result = target.import_bookmark_trash_journal(export_path)

    assert result["imported"] == 1
    assert target.bookmark_trash_journal()[0].session_key == key


def test_import_bookmark_trash_journal_rejects_tampered_export(tmp_path, monkeypatch):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path / "source")
    repository.save(_session("tampered-audit.las"))
    service = LasViewerRecentSessions(repository)
    key = service.list()[0].session_key
    service.set_bookmark(key, label="Original")
    monkeypatch.setattr("services.las_viewer_recent_sessions.time.time_ns", lambda: 123)
    service.remove_bookmark(key)
    export_path = tmp_path / "audit.json"
    service.export_bookmark_trash_journal(export_path)
    payload = json.loads(export_path.read_text(encoding="utf-8"))
    payload["events"][0]["label"] = "Changed"
    export_path.write_text(json.dumps(payload), encoding="utf-8")

    target = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path / "target"))
    try:
        target.import_bookmark_trash_journal(export_path)
    except ValueError as exc:
        assert "integrity" in str(exc)
    else:
        raise AssertionError("ValueError expected")


def test_import_bookmark_trash_journal_append_is_idempotent(tmp_path, monkeypatch):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path / "source")
    repository.save(_session("duplicate-audit.las"))
    source = LasViewerRecentSessions(repository)
    key = source.list()[0].session_key
    source.set_bookmark(key)
    monkeypatch.setattr("services.las_viewer_recent_sessions.time.time_ns", lambda: 456)
    source.remove_bookmark(key)
    export_path = tmp_path / "audit.json"
    source.export_bookmark_trash_journal(export_path)

    target = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path / "target"))
    assert target.import_bookmark_trash_journal(export_path)["imported"] == 1
    second = target.import_bookmark_trash_journal(export_path)
    assert second["imported"] == 0
    assert second["skipped"] == 1


def test_import_bookmark_trash_journal_replace_discards_existing_events(tmp_path, monkeypatch):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path / "source")
    repository.save(_session("replacement-audit.las"))
    source = LasViewerRecentSessions(repository)
    key = source.list()[0].session_key
    source.set_bookmark(key)
    monkeypatch.setattr("services.las_viewer_recent_sessions.time.time_ns", lambda: 789)
    source.remove_bookmark(key)
    export_path = tmp_path / "audit.json"
    source.export_bookmark_trash_journal(export_path)

    target_repository = LasViewerWorkspaceAutosaveRepository(tmp_path / "target")
    target_repository.save(_session("old-audit.las"))
    target = LasViewerRecentSessions(target_repository)
    old_key = target.list()[0].session_key
    target.set_bookmark(old_key)
    monkeypatch.setattr("services.las_viewer_recent_sessions.time.time_ns", lambda: 790)
    target.remove_bookmark(old_key)

    target.import_bookmark_trash_journal(export_path, mode="replace")
    events = target.bookmark_trash_journal()
    assert len(events) == 1
    assert events[0].session_key == key


def test_merge_bookmark_trash_journals_is_deterministic_and_deduplicated(tmp_path, monkeypatch):
    exports = []
    for index, timestamp in enumerate((300, 100)):
        repository = LasViewerWorkspaceAutosaveRepository(tmp_path / f"source-{index}")
        repository.save(_session(f"merge-{index}.las"))
        service = LasViewerRecentSessions(repository)
        key = service.list()[0].session_key
        service.set_bookmark(key, label=f"Merge {index}")
        monkeypatch.setattr("services.las_viewer_recent_sessions.time.time_ns", lambda value=timestamp: value)
        service.remove_bookmark(key)
        path = tmp_path / f"journal-{index}.json"
        service.export_bookmark_trash_journal(path)
        exports.append(path)

    target = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path / "target"))
    result = target.merge_bookmark_trash_journals((exports[0], exports[1], exports[0]))
    events = list(reversed(target.bookmark_trash_journal()))

    assert result["source_count"] == 3
    assert result["imported"] == 2
    assert result["skipped"] == 1
    assert [event.occurred_at_ns for event in events] == [100, 300]


def test_merge_bookmark_trash_journals_is_transactional_on_invalid_source(tmp_path, monkeypatch):
    repository = LasViewerWorkspaceAutosaveRepository(tmp_path / "source")
    repository.save(_session("valid-merge.las"))
    source = LasViewerRecentSessions(repository)
    key = source.list()[0].session_key
    source.set_bookmark(key)
    monkeypatch.setattr("services.las_viewer_recent_sessions.time.time_ns", lambda: 111)
    source.remove_bookmark(key)
    valid = tmp_path / "valid.json"
    source.export_bookmark_trash_journal(valid)
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")

    target = LasViewerRecentSessions(LasViewerWorkspaceAutosaveRepository(tmp_path / "target"))
    try:
        target.merge_bookmark_trash_journals((valid, invalid))
    except ValueError:
        pass
    else:
        raise AssertionError("ValueError expected")

    assert target.bookmark_trash_journal() == ()
