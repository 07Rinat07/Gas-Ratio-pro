from pathlib import Path

SOURCE = Path("app/streamlit_app.py").read_text(encoding="utf-8")


def test_required_gas_mapping_fields_are_strict():
    assert 'REQUIRED_GAS_MAPPING_FIELDS' in SOURCE
    for field in ("c1", "c2", "c3", "ic4", "nc4", "ic5", "nc5"):
        assert f'"{field}"' in SOURCE


def test_invalid_mapping_clears_stale_interpretation_state():
    assert "calculation_blocked_invalid_mapping" in SOURCE
    assert "_clear_invalid_interpretation_state" in SOURCE
    assert "Предыдущие графики и отчеты очищены" in SOURCE


def test_export_uses_inline_progress_not_floating_spinner():
    from core.ui_behavior_contracts import PROFESSIONAL_EXPORT_BEHAVIOR
    from reports.export_progress import staged_progress_reporter

    events = []
    report = staged_progress_reporter(lambda progress, message: events.append((progress, message)))
    report(45, "rendering")

    assert PROFESSIONAL_EXPORT_BEHAVIOR.progress_mode == "inline"
    assert events == [(45, "Шаг 3 из 4 — Формирование документа: rendering")]
