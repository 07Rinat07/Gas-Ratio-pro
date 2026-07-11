from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def test_single_active_governance_set_exists() -> None:
    required = {
        "PROJECT_ROADMAP.md",
        "PROJECT_STATUS.md",
        "ARCHITECTURE.md",
        "DOCUMENTATION_INDEX.md",
    }
    files = {path.name for path in DOCS.iterdir() if path.is_file()}
    assert required <= files
    assert "PROJECT_PROGRESS_NEXT_STEP.md" not in files
    assert "project_plan.md" not in files


def test_roadmap_and_status_reopen_stage_four_until_live_acceptance() -> None:
    roadmap = (DOCS / "PROJECT_ROADMAP.md").read_text(encoding="utf-8")
    status = (DOCS / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    assert "единственная активная последовательность" in roadmap
    assert "Stage 4 — Workbench UI Completion" in roadmap
    assert "IN PROGRESS v204" in roadmap
    assert "Live acceptance" in roadmap
    assert "Petrophysical Engine" in roadmap
    assert "BLOCKED" in roadmap
    assert "Runtime acceptance: **FAILED for v202" in status
    assert "Runtime Error Capture and Workspace Rendering Repair" in status


def test_versioned_roadmaps_and_progress_documents_are_archived() -> None:
    assert not list((DOCS / "02_Roadmap").glob("ROADMAP_v*.md"))
    archive = DOCS / "archive" / "legacy_plans"
    assert (archive / "PROJECT_PROGRESS_NEXT_STEP_v197.md").is_file()
    assert (archive / "project_plan_legacy.md").is_file()
    assert (archive / "versioned_roadmaps").is_dir()


def test_documentation_index_declares_update_policy() -> None:
    index = (DOCS / "DOCUMENTATION_INDEX.md").read_text(encoding="utf-8")
    assert "Единственный активный управляющий комплект" in index
    assert "новые `NEXT_STEP`, `PROGRESS`, `ROADMAP_vN` и `STATUS_vN` файлы запрещены" in index
