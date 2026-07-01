from __future__ import annotations

import json

import pytest

from ai.knowledge_qa import load_knowledge_qa_catalog


def test_default_knowledge_qa_catalog_loads():
    catalog = load_knowledge_qa_catalog()

    assert catalog.version
    assert len(catalog.examples) >= 3
    assert "wh_nan_missing_components" in {example.id for example in catalog.examples}
    assert "ollama_launch_screen" in {example.id for example in catalog.examples}
    assert all(example.sources for example in catalog.examples)


def test_knowledge_qa_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "knowledge_qa.json"
    path.write_text(
        json.dumps(
            {
                "version": "test",
                "examples": [
                    {
                        "id": "same",
                        "question": "Question A?",
                        "answer": "Answer A.",
                        "status": "approved",
                        "priority": 1,
                        "topics": ["test"],
                        "sources": ["docs/formulas.md"],
                        "safety_notes": ["test"],
                    },
                    {
                        "id": "same",
                        "question": "Question B?",
                        "answer": "Answer B.",
                        "status": "approved",
                        "priority": 1,
                        "topics": ["test"],
                        "sources": ["docs/data_format.md"],
                        "safety_notes": ["test"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate"):
        load_knowledge_qa_catalog(path, tmp_path, require_existing_sources=False)


def test_knowledge_qa_rejects_unsafe_sources(tmp_path):
    path = tmp_path / "knowledge_qa.json"
    path.write_text(
        json.dumps(
            {
                "version": "test",
                "examples": [
                    {
                        "id": "unsafe",
                        "question": "Question?",
                        "answer": "Answer.",
                        "status": "approved",
                        "priority": 1,
                        "topics": ["test"],
                        "sources": ["../secret.md"],
                        "safety_notes": ["test"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="safe relative path"):
        load_knowledge_qa_catalog(path, tmp_path, require_existing_sources=False)


def test_knowledge_qa_reports_missing_source_files(tmp_path):
    path = tmp_path / "knowledge_qa.json"
    path.write_text(
        json.dumps(
            {
                "version": "test",
                "examples": [
                    {
                        "id": "missing",
                        "question": "Question?",
                        "answer": "Answer.",
                        "status": "approved",
                        "priority": 1,
                        "topics": ["test"],
                        "sources": ["docs/missing.md"],
                        "safety_notes": ["test"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="not found"):
        load_knowledge_qa_catalog(path, tmp_path)
