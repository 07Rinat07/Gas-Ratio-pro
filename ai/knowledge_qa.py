from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_QA_STATUSES = {"approved", "draft", "reference"}


@dataclass(frozen=True)
class KnowledgeQaExample:
    id: str
    question: str
    answer: str
    status: str
    priority: int
    topics: tuple[str, ...]
    sources: tuple[str, ...]
    safety_notes: tuple[str, ...]


@dataclass(frozen=True)
class KnowledgeQaCatalog:
    version: str
    examples: tuple[KnowledgeQaExample, ...]


def default_knowledge_qa_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "knowledge_qa.json"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_non_empty_string(raw: dict, key: str) -> str:
    value = str(raw.get(key, "")).strip()
    if not value:
        raise ValueError(f"Knowledge Q/A field `{key}` must be a non-empty string.")
    return value


def _read_positive_int(raw: dict, key: str) -> int:
    try:
        value = int(raw.get(key))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Knowledge Q/A field `{key}` must be a positive integer.") from exc

    if value <= 0:
        raise ValueError(f"Knowledge Q/A field `{key}` must be a positive integer.")
    return value


def _read_string_tuple(value: object, key: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"Knowledge Q/A field `{key}` must be a list.")

    items = tuple(str(item).strip() for item in value if str(item).strip())
    if not items:
        raise ValueError(f"Knowledge Q/A field `{key}` must contain at least one item.")
    return items


def _validate_relative_path(path: str) -> None:
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"Knowledge Q/A source path must be a safe relative path: {path}")


def _parse_example(raw_example: object) -> KnowledgeQaExample:
    if not isinstance(raw_example, dict):
        raise ValueError("Knowledge Q/A example entry must be an object.")

    status = _read_non_empty_string(raw_example, "status")
    if status not in SUPPORTED_QA_STATUSES:
        allowed = ", ".join(sorted(SUPPORTED_QA_STATUSES))
        raise ValueError(f"Unsupported Knowledge Q/A status `{status}`. Allowed: {allowed}.")

    sources = tuple(source.replace("\\", "/") for source in _read_string_tuple(raw_example.get("sources"), "sources"))
    for source in sources:
        _validate_relative_path(source)

    return KnowledgeQaExample(
        id=_read_non_empty_string(raw_example, "id"),
        question=_read_non_empty_string(raw_example, "question"),
        answer=_read_non_empty_string(raw_example, "answer"),
        status=status,
        priority=_read_positive_int(raw_example, "priority"),
        topics=_read_string_tuple(raw_example.get("topics"), "topics"),
        sources=sources,
        safety_notes=_read_string_tuple(raw_example.get("safety_notes"), "safety_notes"),
    )


def load_knowledge_qa_catalog(
    path: str | Path | None = None,
    root: str | Path | None = None,
    require_existing_sources: bool = True,
) -> KnowledgeQaCatalog:
    config_path = Path(path) if path is not None else default_knowledge_qa_path()
    resolved_root = Path(root) if root is not None else _project_root()

    with config_path.open("r", encoding="utf-8") as file:
        raw_catalog = json.load(file)

    if not isinstance(raw_catalog, dict):
        raise ValueError("Knowledge Q/A catalog root must be an object.")

    raw_examples = raw_catalog.get("examples")
    if not isinstance(raw_examples, list) or not raw_examples:
        raise ValueError("Knowledge Q/A catalog must contain a non-empty `examples` list.")

    examples = tuple(_parse_example(raw_example) for raw_example in raw_examples)
    example_ids = [example.id for example in examples]
    duplicate_ids = sorted({example_id for example_id in example_ids if example_ids.count(example_id) > 1})
    if duplicate_ids:
        raise ValueError("Duplicate Knowledge Q/A example ids: " + ", ".join(duplicate_ids))

    if require_existing_sources:
        missing_sources = sorted(
            {
                source
                for example in examples
                for source in example.sources
                if not (resolved_root / source).exists()
            }
        )
        if missing_sources:
            raise ValueError("Knowledge Q/A source files not found: " + ", ".join(missing_sources))

    return KnowledgeQaCatalog(
        version=_read_non_empty_string(raw_catalog, "version"),
        examples=examples,
    )
