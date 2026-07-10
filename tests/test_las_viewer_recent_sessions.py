from __future__ import annotations

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
