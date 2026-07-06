from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
PLAN = (ROOT / "docs" / "project_plan.md").read_text(encoding="utf-8")
GUIDE = (ROOT / "docs" / "user_guide.md").read_text(encoding="utf-8")
EULA = (ROOT / "docs" / "eula.md").read_text(encoding="utf-8")


def test_eula_document_exists_with_owner_and_restrictions() -> None:
    assert "End User License Agreement" in EULA
    assert "Rinat Sarmuldin" in EULA
    assert "ura07srr@gmail.com" in EULA
    assert "commercial use" in EULA.lower()
    assert "production deployment" in EULA.lower()
    assert "written permission" in EULA.lower()


def test_license_page_reads_and_renders_eula_document() -> None:
    assert "def _read_application_eula_text()" in SOURCE
    assert 'ROOT_DIR / "docs" / "eula.md"' in SOURCE
    assert "eula-text-panel" in SOURCE
    assert "Full EULA text" in SOURCE
    assert "EULA document" in SOURCE
    assert "EULA placeholder" not in SOURCE


def test_project_plan_marks_eula_as_done_and_points_to_next_item() -> None:
    assert "[x] EULA document." in PLAN
    assert "Licensing and Commercial Protection → EULA document" in PLAN
    assert "Текущий следующий незавершенный пункт: **Licensing and Commercial Protection → License manager**." in PLAN


def test_user_guide_mentions_real_eula_not_placeholder() -> None:
    assert "docs/eula.md" in GUIDE
    assert "EULA document" in GUIDE
    assert "EULA placeholder" not in GUIDE
