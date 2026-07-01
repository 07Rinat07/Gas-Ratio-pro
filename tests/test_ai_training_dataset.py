from __future__ import annotations

import json

import pytest

from ai.knowledge_qa import KnowledgeQaExample
from ai.training_dataset import (
    build_ai_training_pack,
    build_qa_training_record,
    validate_training_text,
    write_ai_training_pack,
)


def test_ai_training_pack_uses_approved_qa_and_eval_cases():
    pack = build_ai_training_pack()

    assert len(pack.train_records) == 6
    assert len(pack.eval_records) == 6
    assert pack.manifest()["safety"]["raw_user_tables_allowed"] is False
    assert all(record.split == "train" for record in pack.train_records)
    assert all(record.split == "eval" for record in pack.eval_records)
    assert "qa::ollama_launch_screen" in {record.id for record in pack.train_records}
    assert "eval::ollama_launch_screen_quality" in {record.id for record in pack.eval_records}


def test_ai_training_record_is_chat_jsonl_compatible():
    example = KnowledgeQaExample(
        id="safe",
        question="Как считается Wh?",
        answer="Wh описан в документации проекта.",
        status="approved",
        priority=1,
        topics=("wh",),
        sources=("docs/formulas.md",),
        safety_notes=("Проверить по ГИС и литологии.",),
    )

    record = build_qa_training_record(example).as_dict()

    assert record["id"] == "qa::safe"
    assert record["messages"][0]["role"] == "system"
    assert record["messages"][1]["role"] == "user"
    assert record["messages"][2]["role"] == "assistant"
    assert record["metadata"]["sources"] == ["docs/formulas.md"]


def test_ai_training_text_rejects_forbidden_terms():
    with pytest.raises(ValueError, match="forbidden term"):
        validate_training_text("bad", "password: secret")


def test_write_ai_training_pack_creates_jsonl_and_manifest(tmp_path):
    report = write_ai_training_pack(output_dir=tmp_path)

    train_lines = (tmp_path / "qa_train.jsonl").read_text(encoding="utf-8").splitlines()
    eval_lines = (tmp_path / "eval_cases.jsonl").read_text(encoding="utf-8").splitlines()
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))

    assert report["ok"] is True
    assert len(train_lines) == manifest["counts"]["train"] == 6
    assert len(eval_lines) == manifest["counts"]["eval"] == 6
    assert json.loads(train_lines[0])["kind"] == "knowledge_qa"
    assert json.loads(eval_lines[0])["kind"] == "ai_eval_case"
