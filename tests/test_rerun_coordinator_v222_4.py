from __future__ import annotations

from pathlib import Path

from core.rerun_coordinator import (
    RERUN_HISTORY_LIMIT,
    begin_rerun_cycle,
    request_rerun,
    rerun_history,
)


def test_only_first_rerun_is_allowed_per_cycle() -> None:
    state: dict[str, object] = {}
    cycle = begin_rerun_cycle(state)
    first = request_rerun(state, "interval_selected", source="test")
    second = request_rerun(state, "format_changed", source="test")

    assert cycle == 1
    assert first.allowed is True
    assert second.allowed is False
    assert second.reason == "interval_selected"
    assert len(rerun_history(state)) == 1


def test_new_cycle_allows_one_new_rerun() -> None:
    state: dict[str, object] = {}
    begin_rerun_cycle(state)
    assert request_rerun(state, "first").allowed is True
    begin_rerun_cycle(state)
    assert request_rerun(state, "second").allowed is True
    assert [item["reason"] for item in rerun_history(state)] == ["first", "second"]


def test_rerun_history_is_bounded() -> None:
    state: dict[str, object] = {}
    for index in range(RERUN_HISTORY_LIMIT + 10):
        begin_rerun_cycle(state)
        request_rerun(state, f"reason-{index}")
    history = rerun_history(state)
    assert len(history) == RERUN_HISTORY_LIMIT
    assert history[-1]["reason"] == f"reason-{RERUN_HISTORY_LIMIT + 9}"


def test_streamlit_app_has_one_direct_rerun_call_inside_gate_only() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert source.count("st.rerun()") == 1
    assert '"workspace_interval_selected"' in source
    assert '"interpretation_interval_selected"' in source
    assert '"ranking_interval_selected"' in source
    assert '"workbench_command_executed"' in source


def test_readme_internal_documentation_map_is_absent() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    forbidden = (
        "## Документация",
        "docs/CHANGELOG.md",
        "docs/formulas.md",
        "docs/user_guide.md",
        "docs/PROJECT_STATUS.md",
        "docs/PROJECT_ROADMAP.md",
    )
    for value in forbidden:
        assert value not in readme
