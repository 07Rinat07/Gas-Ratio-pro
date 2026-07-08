from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCH_REVIEW_DOC = ROOT / "docs" / "09_Architecture" / "ARCHITECTURE_REVIEW_AND_CORE_LTS_FREEZE.md"
PROGRESS_DOC = ROOT / "PROJECT_PROGRESS_NEXT_STEP.md"


def test_architecture_review_document_exists_with_required_gates():
    text = ARCH_REVIEW_DOC.read_text(encoding="utf-8")

    required_sections = (
        "Runtime Gate",
        "Service Boundary Gate",
        "Repository Boundary Gate",
        "Storage Lifecycle Gate",
        "Application State Gate",
        "Documentation Gate",
        "Validation Gate",
        "Core LTS Decision",
        "Sprint 2 Entry Criteria",
    )

    for section in required_sections:
        assert section in text


def test_architecture_review_preserves_core_layer_rules():
    text = ARCH_REVIEW_DOC.read_text(encoding="utf-8")

    required_rules = (
        "UI calls Service Layer only",
        "Repository Layer owns persistent records",
        "Storage Lifecycle owns filesystem cleanup",
        "Application-owned UI state is accessed through `ApplicationStateController`",
        "Destructive operations are routed through `DeleteEngine`",
    )

    for rule in required_rules:
        assert rule in text


def test_project_progress_points_to_core_lts_freeze_before_sprint_2():
    text = PROGRESS_DOC.read_text(encoding="utf-8")

    assert "Architecture Review" in text
    assert "Core LTS Freeze" in text
    assert "Sprint 2 Workspace Framework" in text
    assert text.index("Architecture Review") < text.index("Core LTS Freeze")
    assert text.index("Core LTS Freeze") < text.index("Sprint 2 Workspace Framework")
