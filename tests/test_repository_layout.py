from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_changelog_is_stored_under_docs():
    assert not (ROOT / "CHANGELOG.md").exists()
    assert (ROOT / "docs" / "CHANGELOG.md").exists()


def test_ai_session_history_files_are_not_stored_in_repository_root():
    forbidden = {
        ".aider.chat.history.md",
        ".aider.input.history",
    }

    existing = {path.name for path in ROOT.iterdir() if path.is_file()}

    assert forbidden.isdisjoint(existing)


def test_temporary_roadmap_notes_are_not_stored_in_repository_root():
    forbidden_patterns = (
        "*_SUMMARY.md",
        "*_SUMMARY.txt",
        "*_UPDATE_*.md",
        "PROJECT_CONTINUATION_GUIDE*.txt",
    )

    offenders = []
    for pattern in forbidden_patterns:
        offenders.extend(ROOT.glob(pattern))

    assert offenders == []
