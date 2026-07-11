from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
PLAN = (ROOT / "docs" / "archive" / "legacy_plans" / "project_plan_v5_legacy.md").read_text(encoding="utf-8")
GUIDE = (ROOT / "docs" / "user_guide.md").read_text(encoding="utf-8")
LICENSE = (ROOT / "LICENSE").read_text(encoding="utf-8")


def test_license_is_real_application_tab() -> None:
    assert '"Лицензия",' in SOURCE
    assert '{"label": "Лицензия"' in SOURCE
    assert 'target_tab": "Лицензия"' in SOURCE
    assert 'elif active_tab == "Инструкции и документация"' in SOURCE
    assert '_render_application_licensing_page()' in SOURCE


def test_application_license_page_renders_legal_content() -> None:
    assert 'def _render_application_licensing_page()' in SOURCE
    assert 'application-license-page' in SOURCE
    assert 'license-status-panel' in SOURCE
    assert 'license-cards-grid' in SOURCE
    assert 'license-text-panel' in SOURCE
    assert 'Commercial use' in SOURCE
    assert 'Written permission only' in SOURCE
    assert 'EULA placeholder' not in SOURCE


def test_license_page_uses_repository_license_and_identity() -> None:
    assert 'def _read_application_license_text()' in SOURCE
    assert 'ROOT_DIR / "LICENSE"' in SOURCE
    assert 'Proprietary License' in LICENSE
    assert 'Rinat Sarmuldin' in LICENSE
    assert 'ura07srr@gmail.com' in LICENSE


def test_license_page_is_adaptive_and_not_dashboard_only() -> None:
    assert '.application-license-hero' in SOURCE
    assert '@media (max-width: 1366px)' in SOURCE
    assert '@media (max-width: 760px)' in SOURCE
    assert 'id="license-workspace"' in SOURCE
    assert 'Открыть отдельную страницу лицензии приложения' in SOURCE


def test_license_documentation_updated_without_readme_noise() -> None:
    assert 'Improve application licensing page' in PLAN
    assert 'Application licensing page' in PLAN
    assert 'отдельная вкладка `Лицензия`' in GUIDE
    assert 'EULA placeholder' not in GUIDE
