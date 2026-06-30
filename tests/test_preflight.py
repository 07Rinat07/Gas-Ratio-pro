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
        "config/palettes.json",
        "docs/formulas.md",
        "docs/user_guide.md",
        "examples/sample_gas_data.csv",
        "requirements.txt",
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
        "ai_runtime",
        "logs",
    }


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
