from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def test_active_documentation_entry_points_exist() -> None:
    required = {
        "README.md",
        "PROJECT_ROADMAP.md",
        "PROJECT_STATUS.md",
        "CHANGELOG.md",
        "project_plan.md",
        "PROJECT_PROGRESS_NEXT_STEP.md",
    }
    assert required <= {path.name for path in DOCS.iterdir() if path.is_file()}


def test_roadmap_declares_single_active_sequence() -> None:
    roadmap = (DOCS / "PROJECT_ROADMAP.md").read_text(encoding="utf-8")
    status = (DOCS / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    assert "единственная активная последовательность" in roadmap
    assert "Stage 1 — Visualization Engine completion" in roadmap
    assert "Stage 2 — LAS Viewer completion" in roadmap
    assert "Stage 3 — Modern Workbench and new main page" in roadmap
    assert "Status: **COMPLETED v193**" in roadmap
    assert "### Stage 4 — Workbench UI Completion" in roadmap
    assert "Status: **COMPLETED v197**" in roadmap
    assert "Status: **ACTIVE v197" in roadmap
    assert "Current stage: Petrophysical Engine" in status
    assert "Petrophysical Engine contract audit and enforcement" in status


def test_version_notes_are_archived_outside_docs_root() -> None:
    top_level_version_notes = [
        path.name
        for path in DOCS.iterdir()
        if path.is_file() and any(char.isdigit() for char in path.stem)
        and "V" in path.stem
    ]
    assert top_level_version_notes == []
    assert (DOCS / "archive" / "releases").is_dir()
    assert (DOCS / "archive" / "legacy_plans").is_dir()


def test_compatibility_documents_point_to_active_sources() -> None:
    plan = (DOCS / "project_plan.md").read_text(encoding="utf-8")
    progress = (DOCS / "PROJECT_PROGRESS_NEXT_STEP.md").read_text(encoding="utf-8")
    assert "PROJECT_ROADMAP.md" in plan
    assert "PROJECT_STATUS.md" in plan
    assert "PROJECT_STATUS.md" in progress
