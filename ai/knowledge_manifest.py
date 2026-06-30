from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_KNOWLEDGE_STATUSES = {"approved", "draft", "reference"}


@dataclass(frozen=True)
class KnowledgeSource:
    path: str
    title: str
    status: str
    priority: int
    topics: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class KnowledgeSourceManifest:
    version: str
    default_limit: int
    sources: tuple[KnowledgeSource, ...]


def default_knowledge_manifest_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "knowledge_sources.json"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_non_empty_string(raw: dict, key: str) -> str:
    value = str(raw.get(key, "")).strip()
    if not value:
        raise ValueError(f"Knowledge source field `{key}` must be a non-empty string.")
    return value


def _read_positive_int(raw: dict, key: str) -> int:
    try:
        value = int(raw.get(key))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Knowledge source field `{key}` must be a positive integer.") from exc

    if value <= 0:
        raise ValueError(f"Knowledge source field `{key}` must be a positive integer.")
    return value


def _read_string_tuple(value: object, key: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"Knowledge source field `{key}` must be a list.")

    items = tuple(str(item).strip() for item in value if str(item).strip())
    if not items:
        raise ValueError(f"Knowledge source field `{key}` must contain at least one item.")
    return items


def _validate_relative_path(path: str) -> None:
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"Knowledge source path must be a safe relative path: {path}")


def _parse_source(raw_source: object) -> KnowledgeSource:
    if not isinstance(raw_source, dict):
        raise ValueError("Knowledge source entry must be an object.")

    path = _read_non_empty_string(raw_source, "path").replace("\\", "/")
    _validate_relative_path(path)

    status = _read_non_empty_string(raw_source, "status")
    if status not in SUPPORTED_KNOWLEDGE_STATUSES:
        allowed = ", ".join(sorted(SUPPORTED_KNOWLEDGE_STATUSES))
        raise ValueError(f"Unsupported knowledge source status `{status}`. Allowed: {allowed}.")

    return KnowledgeSource(
        path=path,
        title=_read_non_empty_string(raw_source, "title"),
        status=status,
        priority=_read_positive_int(raw_source, "priority"),
        topics=_read_string_tuple(raw_source.get("topics"), "topics"),
        description=_read_non_empty_string(raw_source, "description"),
    )


def load_knowledge_source_manifest(
    path: str | Path | None = None,
    root: str | Path | None = None,
    require_existing_files: bool = True,
) -> KnowledgeSourceManifest:
    config_path = Path(path) if path is not None else default_knowledge_manifest_path()
    resolved_root = Path(root) if root is not None else _project_root()

    with config_path.open("r", encoding="utf-8") as file:
        raw_manifest = json.load(file)

    if not isinstance(raw_manifest, dict):
        raise ValueError("Knowledge source manifest root must be an object.")

    raw_sources = raw_manifest.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError("Knowledge source manifest must contain a non-empty `sources` list.")

    sources = tuple(_parse_source(raw_source) for raw_source in raw_sources)
    source_paths = [source.path for source in sources]
    duplicate_paths = sorted({path for path in source_paths if source_paths.count(path) > 1})
    if duplicate_paths:
        raise ValueError("Duplicate knowledge source paths: " + ", ".join(duplicate_paths))

    if require_existing_files:
        missing = [source.path for source in sources if not (resolved_root / source.path).exists()]
        if missing:
            raise ValueError("Knowledge source files not found: " + ", ".join(missing))

    return KnowledgeSourceManifest(
        version=_read_non_empty_string(raw_manifest, "version"),
        default_limit=_read_positive_int(raw_manifest, "default_limit"),
        sources=sources,
    )


def knowledge_source_map(manifest: KnowledgeSourceManifest) -> dict[str, KnowledgeSource]:
    return {source.path: source for source in manifest.sources}
