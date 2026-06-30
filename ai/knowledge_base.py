from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ai.knowledge_manifest import (
    KnowledgeSource,
    KnowledgeSourceManifest,
    knowledge_source_map,
    load_knowledge_source_manifest,
)


DEFAULT_DOC_FILES: tuple[str, ...] = (
    "docs/formulas.md",
    "docs/data_format.md",
    "docs/user_guide.md",
    "docs/troubleshooting.md",
    "docs/palettes.md",
    "docs/logging.md",
)


@dataclass(frozen=True)
class KnowledgeChunk:
    source: str
    title: str
    text: str
    status: str = "approved"
    priority: int = 1
    topics: tuple[str, ...] = ()


@dataclass(frozen=True)
class SearchResult:
    chunk: KnowledgeChunk
    score: int


STOP_WORDS = {
    "and",
    "the",
    "with",
    "без",
    "где",
    "для",
    "если",
    "или",
    "как",
    "когда",
    "можно",
    "надо",
    "нужно",
    "при",
    "что",
    "это",
}

DOMAIN_TOKENS = {
    "wh",
    "bh",
    "bar2",
    "pixler",
    "ternary",
    "ch",
    "sumc",
    "c1",
    "c2",
    "c3",
    "ic4",
    "nc4",
    "ic5",
    "nc5",
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[0-9a-zA-Zа-яА-ЯёЁ_Σ]+", text.lower())
    return {
        normalized
        for token in tokens
        if len(normalized := token.replace("ё", "е")) >= 2 and normalized not in STOP_WORDS
    }


def _split_markdown_sections(
    source: str,
    text: str,
    metadata: KnowledgeSource | None = None,
) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    current_title = metadata.title if metadata is not None else Path(source).name
    current_lines: list[str] = []
    status = metadata.status if metadata is not None else "approved"
    priority = metadata.priority if metadata is not None else 1
    topics = metadata.topics if metadata is not None else ()

    for line in text.splitlines():
        if line.startswith("#"):
            if current_lines:
                chunks.append(
                    KnowledgeChunk(
                        source=source,
                        title=current_title,
                        text="\n".join(current_lines).strip(),
                        status=status,
                        priority=priority,
                        topics=topics,
                    )
                )
                current_lines = []
            current_title = line.lstrip("#").strip() or Path(source).name
            continue
        current_lines.append(line)

    if current_lines:
        chunks.append(
            KnowledgeChunk(
                source=source,
                title=current_title,
                text="\n".join(current_lines).strip(),
                status=status,
                priority=priority,
                topics=topics,
            )
        )

    return [chunk for chunk in chunks if chunk.text]


class DocumentationKnowledgeBase:
    def __init__(
        self,
        root: str | Path | None = None,
        doc_files: tuple[str, ...] | None = None,
        manifest: KnowledgeSourceManifest | None = None,
    ) -> None:
        self.root = Path(root) if root is not None else project_root()
        self.doc_files = doc_files
        self.manifest = manifest
        self._chunks: tuple[KnowledgeChunk, ...] | None = None

    def _resolve_sources(self) -> tuple[tuple[str, ...], dict[str, KnowledgeSource]]:
        if self.doc_files is not None:
            return self.doc_files, {}

        manifest = self.manifest or load_knowledge_source_manifest(root=self.root)
        return tuple(source.path for source in manifest.sources), knowledge_source_map(manifest)

    def load_chunks(self) -> tuple[KnowledgeChunk, ...]:
        if self._chunks is not None:
            return self._chunks

        chunks: list[KnowledgeChunk] = []
        doc_files, metadata_by_path = self._resolve_sources()
        for relative_path in doc_files:
            path = self.root / relative_path
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            chunks.extend(_split_markdown_sections(relative_path, text, metadata_by_path.get(relative_path)))

        self._chunks = tuple(chunks)
        return self._chunks

    def search(self, query: str, limit: int = 4) -> tuple[SearchResult, ...]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return ()

        results: list[SearchResult] = []
        for chunk in self.load_chunks():
            chunk_tokens = tokenize(
                f"{chunk.title}\n{chunk.text}\n{chunk.source}\n{' '.join(chunk.topics)}"
            )
            matched_tokens = query_tokens & chunk_tokens
            score = len(matched_tokens)
            if score > 0:
                score += chunk.priority
            score += 3 * len(matched_tokens & DOMAIN_TOKENS)
            if chunk.source == "docs/formulas.md" and matched_tokens & DOMAIN_TOKENS:
                score += 3
            if score > 0:
                results.append(SearchResult(chunk=chunk, score=score))

        results.sort(
            key=lambda result: (result.score, result.chunk.priority, result.chunk.source),
            reverse=True,
        )
        return tuple(results[:limit])

    def build_context(self, query: str, limit: int = 4) -> tuple[str, tuple[str, ...]]:
        results = self.search(query, limit=limit)
        context_parts: list[str] = []
        sources: list[str] = []

        for result in results:
            chunk = result.chunk
            context_parts.append(f"[{chunk.source} :: {chunk.title}]\n{chunk.text}")
            if chunk.source not in sources:
                sources.append(chunk.source)

        return "\n\n".join(context_parts), tuple(sources)
