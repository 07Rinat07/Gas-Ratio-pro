from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.knowledge_base import DocumentationKnowledgeBase  # noqa: E402
from ai.knowledge_manifest import KnowledgeSource, load_knowledge_source_manifest  # noqa: E402


def _source_to_dict(source: KnowledgeSource) -> dict:
    return {
        "path": source.path,
        "title": source.title,
        "status": source.status,
        "priority": source.priority,
        "topics": list(source.topics),
        "description": source.description,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect local AI knowledge base sources.")
    parser.add_argument("--json", action="store_true", help="Print manifest as JSON.")
    parser.add_argument("--query", help="Search the knowledge base.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    manifest = load_knowledge_source_manifest(root=PROJECT_ROOT)
    knowledge_base = DocumentationKnowledgeBase(root=PROJECT_ROOT, manifest=manifest)

    if args.query:
        results = knowledge_base.search(args.query, limit=manifest.default_limit)
        if args.json:
            print(
                json.dumps(
                    [
                        {
                            "source": result.chunk.source,
                            "title": result.chunk.title,
                            "score": result.score,
                            "status": result.chunk.status,
                            "topics": list(result.chunk.topics),
                        }
                        for result in results
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(f"Knowledge search results for: {args.query}")
            for result in results:
                print(
                    f"- {result.chunk.source} :: {result.chunk.title} "
                    f"(score={result.score}, status={result.chunk.status})"
                )
        return 0

    if args.json:
        print(
            json.dumps(
                {
                    "version": manifest.version,
                    "default_limit": manifest.default_limit,
                    "sources": [_source_to_dict(source) for source in manifest.sources],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    chunks = knowledge_base.load_chunks()
    print(f"Local knowledge base manifest ({manifest.version})")
    print(f"Sources: {len(manifest.sources)}")
    print(f"Chunks: {len(chunks)}")
    print("")
    for source in manifest.sources:
        print(f"- {source.path} [{source.status}, priority={source.priority}]")
        print(f"  {source.title}")
        print(f"  topics: {', '.join(source.topics)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
