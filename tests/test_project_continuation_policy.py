from pathlib import Path

from core.build_info import BUILD_VERSION


ROOT = Path(__file__).resolve().parents[1]


def test_canonical_project_plan_exists_in_required_location() -> None:
    plan = ROOT / "docs" / "project" / "PROJECT_PLAN.md"

    assert plan.is_file()
    assert "Следующий разрешённый инкремент" in plan.read_text(encoding="utf-8")


def test_repository_root_contains_only_readme_markdown_documents() -> None:
    unexpected = [
        path.name
        for path in ROOT.glob("*.md")
        if not path.name.startswith("README")
    ]

    assert unexpected == []


def test_deployment_build_matches_runtime_identity() -> None:
    deployment_identity = (ROOT / "DEPLOYMENT_BUILD.txt").read_text(encoding="utf-8").strip()

    assert deployment_identity == f"Gas Ratio Pro {BUILD_VERSION}"
