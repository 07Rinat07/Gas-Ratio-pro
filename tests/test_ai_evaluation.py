from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai.evaluation import load_ai_eval_catalog, run_ai_evaluation


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_default_ai_eval_catalog_loads():
    catalog = load_ai_eval_catalog()

    assert catalog.version
    assert len(catalog.cases) >= 3
    assert "wh_nan_quality" in {case.id for case in catalog.cases}
    assert "ollama_launch_screen_quality" in {case.id for case in catalog.cases}


def test_default_ai_evaluation_passes():
    report = run_ai_evaluation()

    assert report.ok
    assert report.provider_mode == "offline-docs"
    assert report.results
    assert all(result.sources for result in report.results)


def test_configured_provider_mode_uses_ai_settings():
    report = run_ai_evaluation(
        provider_mode="configured",
        config_path=PROJECT_ROOT / "config" / "ai.json",
    )

    assert report.ok
    assert report.provider_mode == "configured"
    assert {result.provider_name for result in report.results} == {"offline-docs"}


def test_unknown_provider_mode_is_rejected():
    with pytest.raises(ValueError, match="Unsupported AI evaluation provider mode"):
        run_ai_evaluation(provider_mode="cloud")


def test_ai_eval_catalog_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "ai_eval_cases.json"
    path.write_text(
        json.dumps(
            {
                "version": "test",
                "cases": [
                    {
                        "id": "same",
                        "question": "Question?",
                        "expected_sources": ["docs/formulas.md"],
                        "required_context_terms": ["Wh"],
                        "required_answer_terms": ["предварительная инженерная подсказка"],
                    },
                    {
                        "id": "same",
                        "question": "Question again?",
                        "expected_sources": ["docs/formulas.md"],
                        "required_context_terms": ["Wh"],
                        "required_answer_terms": ["предварительная инженерная подсказка"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate"):
        load_ai_eval_catalog(path, require_existing_sources=False)


def test_ai_eval_catalog_reports_missing_expected_source(tmp_path):
    path = tmp_path / "ai_eval_cases.json"
    path.write_text(
        json.dumps(
            {
                "version": "test",
                "cases": [
                    {
                        "id": "missing",
                        "question": "Question?",
                        "expected_sources": ["docs/missing.md"],
                        "required_context_terms": ["Wh"],
                        "required_answer_terms": ["предварительная инженерная подсказка"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="not found"):
        load_ai_eval_catalog(path)


def test_ai_evaluation_reports_failed_case(tmp_path):
    path = tmp_path / "ai_eval_cases.json"
    path.write_text(
        json.dumps(
            {
                "version": "test",
                "cases": [
                    {
                        "id": "wrong_source",
                        "question": "Как считается Wh?",
                        "expected_sources": ["docs/data_format.md"],
                        "required_context_terms": ["term-that-does-not-exist"],
                        "required_answer_terms": ["предварительная инженерная подсказка"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = run_ai_evaluation(path=path)

    assert not report.ok
    assert report.results[0].failures
