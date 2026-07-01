from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ai.assistant import LocalAssistant
from ai.factory import build_provider
from ai.knowledge_base import DocumentationKnowledgeBase
from ai.knowledge_qa import load_knowledge_qa_catalog
from ai.settings import load_ai_settings, resolve_ai_config_path


AI_EVAL_PROVIDER_MODES = {"offline-docs", "configured"}


@dataclass(frozen=True)
class AiEvalCase:
    id: str
    question: str
    limit: int
    expected_sources: tuple[str, ...]
    required_context_terms: tuple[str, ...]
    required_answer_terms: tuple[str, ...]
    forbidden_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class AiEvalCatalog:
    version: str
    cases: tuple[AiEvalCase, ...]


@dataclass(frozen=True)
class AiEvalCaseResult:
    case_id: str
    question: str
    passed: bool
    failures: tuple[str, ...]
    sources: tuple[str, ...]
    provider_name: str


@dataclass(frozen=True)
class AiEvalReport:
    version: str
    provider_mode: str
    results: tuple[AiEvalCaseResult, ...]

    @property
    def ok(self) -> bool:
        return all(result.passed for result in self.results)

    def as_dict(self) -> dict:
        return {
            "version": self.version,
            "provider_mode": self.provider_mode,
            "ok": self.ok,
            "results": [
                {
                    "case_id": result.case_id,
                    "question": result.question,
                    "passed": result.passed,
                    "failures": list(result.failures),
                    "sources": list(result.sources),
                    "provider_name": result.provider_name,
                }
                for result in self.results
            ],
        }


def default_ai_eval_cases_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "ai_eval_cases.json"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_non_empty_string(raw: dict, key: str) -> str:
    value = str(raw.get(key, "")).strip()
    if not value:
        raise ValueError(f"AI eval case field `{key}` must be a non-empty string.")
    return value


def _read_positive_int(raw: dict, key: str, default: int) -> int:
    try:
        value = int(raw.get(key, default))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"AI eval case field `{key}` must be a positive integer.") from exc

    if value <= 0:
        raise ValueError(f"AI eval case field `{key}` must be a positive integer.")
    return value


def _read_string_tuple(value: object, key: str, allow_empty: bool = False) -> tuple[str, ...]:
    if value is None and allow_empty:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"AI eval case field `{key}` must be a list.")

    items = tuple(str(item).strip() for item in value if str(item).strip())
    if not items and not allow_empty:
        raise ValueError(f"AI eval case field `{key}` must contain at least one item.")
    return items


def _validate_relative_reference(reference: str) -> None:
    path_part = reference.split("#", maxsplit=1)[0]
    candidate = Path(path_part)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"AI eval source must be a safe relative reference: {reference}")


def _parse_case(raw_case: object) -> AiEvalCase:
    if not isinstance(raw_case, dict):
        raise ValueError("AI eval case entry must be an object.")

    return AiEvalCase(
        id=_read_non_empty_string(raw_case, "id"),
        question=_read_non_empty_string(raw_case, "question"),
        limit=_read_positive_int(raw_case, "limit", 4),
        expected_sources=_read_string_tuple(raw_case.get("expected_sources"), "expected_sources"),
        required_context_terms=_read_string_tuple(raw_case.get("required_context_terms"), "required_context_terms"),
        required_answer_terms=_read_string_tuple(raw_case.get("required_answer_terms"), "required_answer_terms"),
        forbidden_terms=_read_string_tuple(raw_case.get("forbidden_terms"), "forbidden_terms", allow_empty=True),
    )


def _validate_expected_sources(cases: tuple[AiEvalCase, ...], root: Path) -> None:
    qa_catalog = load_knowledge_qa_catalog(root=root)
    qa_ids = {example.id for example in qa_catalog.examples}

    for case in cases:
        for source in case.expected_sources:
            _validate_relative_reference(source)
            path_part, _, fragment = source.partition("#")
            if not (root / path_part).exists():
                raise ValueError(f"AI eval expected source file not found: {source}")
            if path_part == "config/knowledge_qa.json" and fragment and fragment not in qa_ids:
                raise ValueError(f"AI eval expected Q/A id not found: {source}")


def load_ai_eval_catalog(
    path: str | Path | None = None,
    root: str | Path | None = None,
    require_existing_sources: bool = True,
) -> AiEvalCatalog:
    resolved_root = Path(root) if root is not None else _project_root()
    config_path = Path(path) if path is not None else resolved_root / "config" / "ai_eval_cases.json"

    with config_path.open("r", encoding="utf-8") as file:
        raw_catalog = json.load(file)

    if not isinstance(raw_catalog, dict):
        raise ValueError("AI eval catalog root must be an object.")

    raw_cases = raw_catalog.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("AI eval catalog must contain a non-empty `cases` list.")

    cases = tuple(_parse_case(raw_case) for raw_case in raw_cases)
    case_ids = [case.id for case in cases]
    duplicate_ids = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
    if duplicate_ids:
        raise ValueError("Duplicate AI eval case ids: " + ", ".join(duplicate_ids))

    if require_existing_sources:
        _validate_expected_sources(cases, resolved_root)

    return AiEvalCatalog(
        version=_read_non_empty_string(raw_catalog, "version"),
        cases=cases,
    )


def _contains(text: str, term: str) -> bool:
    return term.casefold() in text.casefold()


def _evaluate_case(case: AiEvalCase, assistant: LocalAssistant) -> AiEvalCaseResult:
    answer = assistant.answer(case.question, limit=case.limit)
    prompt = answer.prompt
    failures: list[str] = []

    for source in case.expected_sources:
        if source not in answer.sources:
            failures.append(f"Expected source missing: {source}")

    for term in case.required_context_terms:
        if not _contains(prompt, term):
            failures.append(f"Required context term missing: {term}")

    for term in case.required_answer_terms:
        if not _contains(answer.answer, term):
            failures.append(f"Required answer term missing: {term}")

    combined_text = f"{prompt}\n{answer.answer}"
    for term in case.forbidden_terms:
        if _contains(combined_text, term):
            failures.append(f"Forbidden term found: {term}")

    return AiEvalCaseResult(
        case_id=case.id,
        question=case.question,
        passed=not failures,
        failures=tuple(failures),
        sources=answer.sources,
        provider_name=answer.provider_name,
    )


def _build_assistant(
    root: Path,
    provider_mode: str,
    config_path: str | Path | None = None,
) -> LocalAssistant:
    provider = None
    if provider_mode == "configured":
        settings = load_ai_settings(config_path or resolve_ai_config_path(root))
        provider = build_provider(settings)
    return LocalAssistant(
        knowledge_base=DocumentationKnowledgeBase(root=root),
        provider=provider,
    )


def run_ai_evaluation(
    root: str | Path | None = None,
    path: str | Path | None = None,
    assistant: LocalAssistant | None = None,
    provider_mode: str = "offline-docs",
    config_path: str | Path | None = None,
) -> AiEvalReport:
    resolved_root = Path(root) if root is not None else _project_root()
    if provider_mode not in AI_EVAL_PROVIDER_MODES:
        allowed = ", ".join(sorted(AI_EVAL_PROVIDER_MODES))
        raise ValueError(f"Unsupported AI evaluation provider mode: {provider_mode}. Allowed: {allowed}.")

    catalog = load_ai_eval_catalog(path=path, root=resolved_root)
    resolved_assistant = assistant or _build_assistant(
        resolved_root,
        provider_mode,
        config_path=config_path,
    )
    results = tuple(_evaluate_case(case, resolved_assistant) for case in catalog.cases)
    return AiEvalReport(version=catalog.version, provider_mode=provider_mode, results=results)
