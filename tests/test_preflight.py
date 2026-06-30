from __future__ import annotations

import json
import shutil
from pathlib import Path

from core.preflight import run_preflight


def _copy_required_fixture_tree(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[1]
    root = tmp_path / "project"
    root.mkdir()

    for relative in (
        "app/streamlit_app.py",
        "config/ai.json",
        "config/ai_eval_cases.json",
        "config/ai_model_profiles.json",
        "config/knowledge_qa.json",
        "config/knowledge_sources.json",
        "config/palettes.json",
        "docs/ai_evaluation.md",
        "docs/ai_usage.md",
        "docs/data_format.md",
        "docs/formulas.md",
        "docs/knowledge_base.md",
        "docs/local_model_profiles.md",
        "docs/logging.md",
        "docs/palettes.md",
        "docs/troubleshooting.md",
        "docs/user_guide.md",
        "examples/sample_gas_data.csv",
        "requirements.txt",
        "scripts/ai_models.py",
        "scripts/evaluate_ai.py",
        "scripts/knowledge_base.py",
    ):
        source = source_root / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    return root


def test_preflight_passes_for_offline_docs_fixture(tmp_path):
    root = _copy_required_fixture_tree(tmp_path)

    report = run_preflight(root)

    assert report.ok
    assert {check.name for check in report.checks} >= {
        "python",
        "project_files",
        "dependencies",
        "palette_config",
        "ai_model_profiles",
        "knowledge_sources",
        "knowledge_qa",
        "ai_evaluation",
        "ai_runtime",
        "logs",
    }


def test_preflight_reports_invalid_ai_model_profiles(tmp_path):
    root = _copy_required_fixture_tree(tmp_path)
    (root / "config" / "ai_model_profiles.json").write_text(
        json.dumps({"version": "bad", "source": "bad", "source_urls": [], "profiles": []}),
        encoding="utf-8",
    )

    report = run_preflight(root)
    profiles_check = next(check for check in report.checks if check.name == "ai_model_profiles")

    assert not report.ok
    assert profiles_check.status == "error"
    assert "profiles" in profiles_check.message


def test_preflight_reports_invalid_knowledge_sources(tmp_path):
    root = _copy_required_fixture_tree(tmp_path)
    (root / "config" / "knowledge_sources.json").write_text(
        json.dumps({"version": "bad", "default_limit": 4, "sources": []}),
        encoding="utf-8",
    )

    report = run_preflight(root)
    sources_check = next(check for check in report.checks if check.name == "knowledge_sources")

    assert not report.ok
    assert sources_check.status == "error"
    assert "sources" in sources_check.message


def test_preflight_reports_invalid_knowledge_qa(tmp_path):
    root = _copy_required_fixture_tree(tmp_path)
    (root / "config" / "knowledge_qa.json").write_text(
        json.dumps({"version": "bad", "examples": []}),
        encoding="utf-8",
    )

    report = run_preflight(root)
    qa_check = next(check for check in report.checks if check.name == "knowledge_qa")

    assert not report.ok
    assert qa_check.status == "error"
    assert "examples" in qa_check.message


def test_preflight_reports_failed_ai_evaluation(tmp_path):
    root = _copy_required_fixture_tree(tmp_path)
    (root / "config" / "ai_eval_cases.json").write_text(
        json.dumps(
            {
                "version": "bad",
                "cases": [
                    {
                        "id": "bad_case",
                        "question": "Как считается Wh?",
                        "expected_sources": ["docs/data_format.md"],
                        "required_context_terms": ["term-that-does-not-exist"],
                        "required_answer_terms": ["Локальный помощник"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = run_preflight(root)
    eval_check = next(check for check in report.checks if check.name == "ai_evaluation")

    assert not report.ok
    assert eval_check.status == "error"
    assert "bad_case" in eval_check.message


def test_preflight_reports_invalid_ai_config(tmp_path):
    root = _copy_required_fixture_tree(tmp_path)
    (root / "config" / "ai.json").write_text(
        json.dumps({"provider": "cloud-api"}),
        encoding="utf-8",
    )

    report = run_preflight(root)
    ai_check = next(check for check in report.checks if check.name == "ai_config")

    assert not report.ok
    assert ai_check.status == "error"
    assert "Unsupported AI provider" in ai_check.message


def test_preflight_ollama_ready_with_fake_local_model(tmp_path):
    root = _copy_required_fixture_tree(tmp_path)
    (root / "config" / "ai.json").write_text(
        json.dumps(
            {
                "provider": "ollama",
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model": "local-model",
                    "timeout_seconds": 3,
                },
            }
        ),
        encoding="utf-8",
    )

    def fake_http_get(url: str, timeout_seconds: int) -> dict:
        return {"models": [{"name": "local-model"}]}

    report = run_preflight(root, http_get=fake_http_get)

    assert report.ok
    assert "Ollama готов" in next(check.message for check in report.checks if check.name == "ai_runtime")
