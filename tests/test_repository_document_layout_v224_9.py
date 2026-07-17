"""Repository layout guard for root-level documentation."""

from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRIMARY_README = re.compile(r"^README(?:\.[A-Za-z0-9_-]+)?\.md$", re.IGNORECASE)


def test_only_primary_readmes_are_markdown_files_at_project_root() -> None:
    unexpected = sorted(
        path.name
        for path in PROJECT_ROOT.glob("*.md")
        if not PRIMARY_README.fullmatch(path.name)
    )

    assert unexpected == [], (
        "Non-README Markdown documentation must be stored under docs/: "
        + ", ".join(unexpected)
    )


def test_release_changelogs_are_archived_under_docs() -> None:
    release_dir = PROJECT_ROOT / "docs" / "archive" / "releases"
    expected = {
        "CHANGELOG_v224.0.md",
        "CHANGELOG_v224.2.md",
        "CHANGELOG_v224.3.md",
        "CHANGELOG_v224.4.md",
        "CHANGELOG_v224.5.md",
        "CHANGELOG_v224.6.md",
        "CHANGELOG_v224.7.md",
        "CHANGELOG_v224.8.md",
    }

    assert expected.issubset({path.name for path in release_dir.glob("CHANGELOG_v224.*.md")})
