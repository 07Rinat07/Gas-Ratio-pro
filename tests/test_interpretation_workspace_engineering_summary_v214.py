from pathlib import Path


def test_data_workspace_uses_engineering_interval_summary() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert 'st.subheader("Инженерная сводка интерпретации")' in source
    assert "workspace_interval_summary = engineering_interval_summary(calculated_df)" in source
    assert 'st.subheader("Сводка классификации")' not in source
    assert "summarize_interpretation(calculated_df)" not in source


def test_active_roadmap_contains_interpretation_2_definition_of_done() -> None:
    roadmap = Path("docs/PROJECT_ROADMAP.md").read_text(encoding="utf-8")
    assert "Reservoir Intelligence / Interpretation 2.0" in roadmap
    assert "Pixler rehabilitation" in roadmap
    assert "Ternary rehabilitation" in roadmap
    assert "Depth engineering panel" in roadmap
    assert "Definition of Done" in roadmap
