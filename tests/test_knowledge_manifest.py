from __future__ import annotations

import json

import pytest

from ai.knowledge_manifest import load_knowledge_source_manifest


def test_default_knowledge_manifest_loads():
    manifest = load_knowledge_source_manifest()

    assert manifest.version
    assert manifest.default_limit > 0
    assert "docs/formulas.md" in {source.path for source in manifest.sources}
    assert all(source.priority > 0 for source in manifest.sources)


def test_knowledge_manifest_rejects_duplicate_paths(tmp_path):
    path = tmp_path / "knowledge_sources.json"
    path.write_text(
        json.dumps(
            {
                "version": "test",
                "default_limit": 4,
                "sources": [
                    {
                        "path": "docs/a.md",
                        "title": "A",
                        "status": "approved",
                        "priority": 1,
                        "topics": ["test"],
                        "description": "test",
                    },
                    {
                        "path": "docs/a.md",
                        "title": "A duplicate",
                        "status": "approved",
                        "priority": 1,
                        "topics": ["test"],
                        "description": "test",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate knowledge source paths"):
        load_knowledge_source_manifest(path, tmp_path, require_existing_files=False)


def test_knowledge_manifest_rejects_unsafe_paths(tmp_path):
    path = tmp_path / "knowledge_sources.json"
    path.write_text(
        json.dumps(
            {
                "version": "test",
                "default_limit": 4,
                "sources": [
                    {
                        "path": "../secret.md",
                        "title": "Secret",
                        "status": "approved",
                        "priority": 1,
                        "topics": ["test"],
                        "description": "test",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="safe relative path"):
        load_knowledge_source_manifest(path, tmp_path, require_existing_files=False)


def test_knowledge_manifest_reports_missing_files(tmp_path):
    path = tmp_path / "knowledge_sources.json"
    path.write_text(
        json.dumps(
            {
                "version": "test",
                "default_limit": 4,
                "sources": [
                    {
                        "path": "docs/missing.md",
                        "title": "Missing",
                        "status": "approved",
                        "priority": 1,
                        "topics": ["test"],
                        "description": "test",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="not found"):
        load_knowledge_source_manifest(path, tmp_path)
