from __future__ import annotations

from app import streamlit_app


def test_modern_workbench_is_default_production_entry_point(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.delenv(streamlit_app.LEGACY_UI_ENV_VAR, raising=False)
    monkeypatch.setattr(streamlit_app, "_run_modern_workbench", lambda: calls.append("modern"))
    monkeypatch.setattr(streamlit_app, "_run_legacy_ui", lambda: calls.append("legacy"))

    streamlit_app.main()

    assert calls == ["modern"]


def test_legacy_ui_requires_explicit_process_environment_flag(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setenv(streamlit_app.LEGACY_UI_ENV_VAR, "true")
    monkeypatch.setattr(streamlit_app, "_run_modern_workbench", lambda: calls.append("modern"))
    monkeypatch.setattr(streamlit_app, "_run_legacy_ui", lambda: calls.append("legacy"))

    streamlit_app.main()

    assert calls == ["legacy"]


def test_session_state_cannot_enable_legacy_ui(monkeypatch) -> None:
    monkeypatch.delenv(streamlit_app.LEGACY_UI_ENV_VAR, raising=False)
    streamlit_app.st.session_state[streamlit_app.LEGACY_UI_ENV_VAR] = "true"

    assert streamlit_app.legacy_ui_requested() is False


def test_legacy_flag_parser_is_strict() -> None:
    assert streamlit_app.legacy_ui_requested({streamlit_app.LEGACY_UI_ENV_VAR: "1"}) is True
    assert streamlit_app.legacy_ui_requested({streamlit_app.LEGACY_UI_ENV_VAR: "ON"}) is True
    assert streamlit_app.legacy_ui_requested({streamlit_app.LEGACY_UI_ENV_VAR: "legacy"}) is False
    assert streamlit_app.legacy_ui_requested({}) is False
