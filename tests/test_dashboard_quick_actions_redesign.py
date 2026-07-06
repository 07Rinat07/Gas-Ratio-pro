from pathlib import Path

SOURCE = Path("app/streamlit_app.py").read_text(encoding="utf-8")


def test_quick_actions_have_compact_registry_fields():
    assert '"icon": "📁"' in SOURCE
    assert '"short_title": "Проект"' in SOURCE
    assert '"icon": "🧰"' in SOURCE
    assert '"short_title": "LAS Editor"' in SOURCE
    assert 'def _quick_action_button_label' in SOURCE


def test_quick_action_summary_does_not_repeat_open_button_copy():
    assert "quick-action-summary" in SOURCE
    assert "compact-quick-action-summary" in SOURCE
    assert "Нажмите одноименную кнопку ниже" not in SOURCE
    assert "Нажмите одноименную кнопку ниже" not in SOURCE
    assert "Последнее действие" in SOURCE


def test_start_tab_documents_redesigned_quick_actions_css():
    assert "quick-actions-redesigned" in SOURCE
    assert "Компактная панель: одна плитка = одно действие" in SOURCE
    assert "help=action[\"tooltip\"]" in SOURCE
    assert "_quick_action_button_label(action)" in SOURCE
    assert "functional-quick-actions div[data-testid=\"stButton\"] > button" in SOURCE
