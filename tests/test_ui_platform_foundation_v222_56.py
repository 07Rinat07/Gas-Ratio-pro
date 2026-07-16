from __future__ import annotations

from ui_platform import ButtonSpec, EmptyStateSpec, StreamlitUIAdapter, ThemeEngine


class FakeStreamlit:
    def __init__(self) -> None:
        self.markdowns: list[str] = []
        self.buttons: list[tuple[str, dict]] = []

    def markdown(self, value: str, **kwargs):
        self.markdowns.append(value)

    def button(self, label: str, **kwargs):
        self.buttons.append((label, kwargs))
        return False


def test_theme_engine_exposes_central_tokens():
    engine = ThemeEngine()
    assert engine.active.theme_id == "dark"
    assert engine.active.tokens.colors.primary.startswith("#")
    assert engine.active.tokens.spacing.md > engine.active.tokens.spacing.sm


def test_component_contracts_are_json_safe():
    spec = EmptyStateSpec(
        title="No data",
        message="Import a dataset.",
        details=("Open Import Workspace",),
        action=ButtonSpec("Import", "import-action", variant="primary", compact=True),
    )
    payload = spec.to_dict()
    assert payload["title"] == "No data"
    assert payload["action"]["key"] == "import-action"


def test_streamlit_adapter_renders_empty_state_without_domain_objects():
    st = FakeStreamlit()
    adapter = StreamlitUIAdapter(st)
    assert adapter.empty_state(EmptyStateSpec("No data", "Import data.")) is False
    assert "gr-empty-state" in st.markdowns[0]


def test_streamlit_button_uses_content_width():
    st = FakeStreamlit()
    StreamlitUIAdapter(st).button(ButtonSpec("RU", "lang-ru", compact=True))
    assert st.buttons[0][1]["width"] == "content"
