from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_is_project_overview_not_development_diary():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    forbidden_fragments = [
        "Roadmap 2.0 status",
        "Текущий завершенный инкремент",
        "Next major module",
        "current increment",
        "v22 Reporting behavior",
        "Status: frozen public API",
        "Validation Dataset v2 passes",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in readme


def test_readme_exposes_only_public_multilingual_documentation_entrypoints():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for path in ("docs/user/ru/index.md", "docs/user/kk/index.md", "docs/user/en/index.md"):
        assert path in readme
    for internal in ("docs/CHANGELOG.md", "docs/PROJECT_STATUS.md", "docs/PROJECT_ROADMAP.md"):
        assert internal not in readme


def test_readme_policy_document_exists():
    policy_path = ROOT / "docs" / "README_POLICY.md"
    assert policy_path.exists()
    policy = policy_path.read_text(encoding="utf-8")
    assert "README.md must not be used as a development diary" in policy
