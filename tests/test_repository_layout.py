from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

ROOT_DOCUMENT_ALLOWLIST = {
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
}

FORBIDDEN_ROOT_DOCUMENT_PREFIXES = (
    "GAS_RATIO_PRO_ROADMAP_",
    "PROJECT_CONTINUATION_GUIDE_",
)


def test_roadmap_documents_are_not_stored_in_repository_root():
    """Roadmap and continuation docs must live under docs/, not repo root."""
    forbidden_files = [
        path.name
        for path in REPO_ROOT.iterdir()
        if path.is_file()
        and path.name.startswith(FORBIDDEN_ROOT_DOCUMENT_PREFIXES)
    ]

    assert forbidden_files == []


def test_allowed_root_markdown_files_are_explicit():
    """Keep root clean: only operational markdown files may stay in root."""
    root_markdown_files = {
        path.name
        for path in REPO_ROOT.iterdir()
        if path.is_file() and not path.name.startswith(".") and path.suffix.lower() == ".md"
    }

    assert root_markdown_files <= ROOT_DOCUMENT_ALLOWLIST


def test_roadmap_summary_exists_under_docs():
    roadmap_summary = REPO_ROOT / "docs" / "02_Roadmap" / "GAS_RATIO_PRO_ROADMAP_v4_SUMMARY.txt"

    assert roadmap_summary.exists()
    assert roadmap_summary.is_file()
