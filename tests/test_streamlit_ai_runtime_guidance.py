from __future__ import annotations

from app.streamlit_app import _build_recommended_ai_setup_commands


def test_streamlit_ai_runtime_guidance_uses_balanced_profile_commands():
    commands = _build_recommended_ai_setup_commands()

    assert "ollama pull qwen3:4b" in commands
    assert "python scripts/preflight.py" in commands
    assert "python scripts/evaluate_ai.py --provider-mode configured" in commands
