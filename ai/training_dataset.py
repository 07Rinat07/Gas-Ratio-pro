from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai.evaluation import AiEvalCase, load_ai_eval_catalog
from ai.knowledge_qa import KnowledgeQaExample, load_knowledge_qa_catalog


TRAINING_SYSTEM_PROMPT = (
    "Ты локальный инженерный AI-помощник Gas Ratio Interpreter. "
    "Отвечай только по проверенной документации проекта, не придумывай новые "
    "формулы и всегда напоминай, что интерпретация является предварительной "
    "инженерной подсказкой."
)
FORBIDDEN_TRAINING_TEXT_TERMS = (
    "api key",
    "password",
    "secret",
    "private key",
    "пароль",
    "секрет",
    "токен доступа",
)


@dataclass(frozen=True)
class AiTrainingRecord:
    id: str
    kind: str
    split: str
    messages: tuple[dict[str, str], ...]
    metadata: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "split": self.split,
            "messages": list(self.messages),
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class AiTrainingPack:
    version: str
    train_records: tuple[AiTrainingRecord, ...]
    eval_records: tuple[AiTrainingRecord, ...]

    @property
    def total_records(self) -> int:
        return len(self.train_records) + len(self.eval_records)

    def manifest(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "format": "jsonl-chat-records",
            "safety": {
                "raw_user_tables_allowed": False,
                "approved_qa_only_by_default": True,
                "forbidden_training_text_terms": list(FORBIDDEN_TRAINING_TEXT_TERMS),
            },
            "files": {
                "train": "qa_train.jsonl",
                "eval": "eval_cases.jsonl",
            },
            "counts": {
                "train": len(self.train_records),
                "eval": len(self.eval_records),
                "total": self.total_records,
            },
        }


def default_ai_training_pack_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "artifacts" / "ai_training_pack"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _contains_forbidden_training_text(text: str) -> str | None:
    lowered = text.casefold()
    for term in FORBIDDEN_TRAINING_TEXT_TERMS:
        if term.casefold() in lowered:
            return term
    return None


def validate_training_text(record_id: str, *texts: str) -> None:
    for text in texts:
        forbidden_term = _contains_forbidden_training_text(text)
        if forbidden_term is not None:
            raise ValueError(
                f"AI training record `{record_id}` contains forbidden term `{forbidden_term}`."
            )


def _qa_answer_with_safety(example: KnowledgeQaExample) -> str:
    safety = "\n".join(f"- {note}" for note in example.safety_notes)
    return (
        f"{example.answer}\n\n"
        "Ограничения и безопасность:\n"
        f"{safety}"
    )


def build_qa_training_record(example: KnowledgeQaExample) -> AiTrainingRecord:
    answer = _qa_answer_with_safety(example)
    validate_training_text(example.id, example.question, answer)
    return AiTrainingRecord(
        id=f"qa::{example.id}",
        kind="knowledge_qa",
        split="train",
        messages=(
            {"role": "system", "content": TRAINING_SYSTEM_PROMPT},
            {"role": "user", "content": example.question},
            {"role": "assistant", "content": answer},
        ),
        metadata={
            "status": example.status,
            "topics": list(example.topics),
            "sources": list(example.sources),
            "priority": example.priority,
        },
    )


def build_eval_training_record(case: AiEvalCase) -> AiTrainingRecord:
    validate_training_text(
        case.id,
        case.question,
        "\n".join(case.required_context_terms),
        "\n".join(case.required_answer_terms),
    )
    return AiTrainingRecord(
        id=f"eval::{case.id}",
        kind="ai_eval_case",
        split="eval",
        messages=(
            {"role": "system", "content": TRAINING_SYSTEM_PROMPT},
            {"role": "user", "content": case.question},
        ),
        metadata={
            "limit": case.limit,
            "expected_sources": list(case.expected_sources),
            "required_context_terms": list(case.required_context_terms),
            "required_answer_terms": list(case.required_answer_terms),
            "forbidden_terms": list(case.forbidden_terms),
        },
    )


def build_ai_training_pack(
    root: str | Path | None = None,
    include_draft: bool = False,
) -> AiTrainingPack:
    resolved_root = Path(root) if root is not None else _project_root()
    qa_catalog = load_knowledge_qa_catalog(root=resolved_root)
    eval_catalog = load_ai_eval_catalog(root=resolved_root)

    allowed_statuses = {"approved", "reference"} if not include_draft else {"approved", "reference", "draft"}
    train_records = tuple(
        build_qa_training_record(example)
        for example in qa_catalog.examples
        if example.status in allowed_statuses
    )
    eval_records = tuple(build_eval_training_record(case) for case in eval_catalog.cases)

    if not train_records:
        raise ValueError("AI training pack must contain at least one training Q/A record.")
    if not eval_records:
        raise ValueError("AI training pack must contain at least one evaluation record.")

    return AiTrainingPack(
        version=f"{qa_catalog.version}+{eval_catalog.version}",
        train_records=train_records,
        eval_records=eval_records,
    )


def write_jsonl(path: str | Path, records: tuple[AiTrainingRecord, ...]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(record.as_dict(), ensure_ascii=False, sort_keys=True)
        for record in records
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_ai_training_pack(
    output_dir: str | Path | None = None,
    root: str | Path | None = None,
    include_draft: bool = False,
) -> dict[str, Any]:
    resolved_output_dir = Path(output_dir) if output_dir is not None else default_ai_training_pack_dir()
    pack = build_ai_training_pack(root=root, include_draft=include_draft)

    train_path = resolved_output_dir / "qa_train.jsonl"
    eval_path = resolved_output_dir / "eval_cases.jsonl"
    manifest_path = resolved_output_dir / "manifest.json"

    write_jsonl(train_path, pack.train_records)
    write_jsonl(eval_path, pack.eval_records)
    manifest = pack.manifest()
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "ok": True,
        "output_dir": str(resolved_output_dir),
        "train_path": str(train_path),
        "eval_path": str(eval_path),
        "manifest_path": str(manifest_path),
        "manifest": manifest,
    }
