from __future__ import annotations

import json
from collections.abc import Sequence

from ai.local_agent_setup import (
    CommandResult,
    LocalAgentSetupOptions,
    build_local_agent_next_commands,
    run_local_agent_setup,
)
from ai.model_profiles import find_ai_model_profile, load_ai_model_profile_catalog
from ai.settings import load_ai_settings


def test_local_agent_setup_dry_run_does_not_call_ollama():
    calls: list[tuple[str, ...]] = []

    def runner(args: Sequence[str], timeout_seconds: int) -> CommandResult:
        calls.append(tuple(args))
        return CommandResult(returncode=0)

    report = run_local_agent_setup(runner=runner)

    assert report.ok
    assert report.profile.id == "balanced"
    assert not calls
    assert any(step.name == "knowledge_training_pack" for step in report.steps)
    assert f"ollama pull {report.profile.model}" in report.next_commands


def test_local_agent_next_commands_include_config_and_evaluation():
    catalog = load_ai_model_profile_catalog()
    profile = find_ai_model_profile(catalog, "balanced")

    assert profile is not None
    commands = build_local_agent_next_commands(profile)

    assert f"ollama pull {profile.model}" in commands
    assert f"python scripts/ai_config.py ollama --profile {profile.id} --write" in commands
    assert "python scripts/evaluate_ai.py --provider-mode configured" in commands


def test_local_agent_setup_reports_missing_ollama_when_download_requested():
    def runner(args: Sequence[str], timeout_seconds: int) -> CommandResult:
        assert tuple(args) == ("ollama", "--version")
        return CommandResult(returncode=127, stderr="not found")

    report = run_local_agent_setup(
        options=LocalAgentSetupOptions(pull_model=True),
        runner=runner,
    )

    assert not report.ok
    assert next(step for step in report.steps if step.name == "ollama_cli").status == "error"


def test_local_agent_setup_writes_config_when_runtime_is_ready(tmp_path):
    config_path = tmp_path / "ai.json"

    def fake_http_get(url: str, timeout_seconds: int) -> dict:
        assert url.endswith("/api/tags")
        return {"models": [{"name": "qwen3:4b"}]}

    report = run_local_agent_setup(
        options=LocalAgentSetupOptions(write_config=True),
        config_path=config_path,
        http_get=fake_http_get,
    )
    settings = load_ai_settings(config_path)

    assert report.ok
    assert settings.provider == "ollama"
    assert settings.ollama.model == "qwen3:4b"
    assert next(step for step in report.steps if step.name == "ai_runtime").status == "ok"


def test_local_agent_setup_runs_configured_evaluation_with_custom_config(tmp_path):
    config_path = tmp_path / "ai.json"
    config_path.write_text(
        json.dumps(
            {
                "provider": "offline-docs",
                "privacy": {
                    "send_full_table": False,
                    "send_selected_interval_only": True,
                },
            }
        ),
        encoding="utf-8",
    )

    report = run_local_agent_setup(
        options=LocalAgentSetupOptions(run_configured_evaluation=True),
        config_path=config_path,
    )

    assert report.ok
    assert next(step for step in report.steps if step.name == "configured_evaluation").status == "ok"
