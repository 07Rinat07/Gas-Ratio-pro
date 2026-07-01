from __future__ import annotations

from app.streamlit_app import (
    AI_SUPPORT_CHAT_KEY,
    AI_SUPPORT_QUICK_QUESTIONS,
    AI_SUPPORT_WELCOME_MESSAGE,
    _append_ai_support_chat_message,
    _build_recommended_ai_setup_commands,
    _initial_ai_support_chat_messages,
)


def test_streamlit_ai_runtime_guidance_uses_balanced_profile_commands():
    commands = _build_recommended_ai_setup_commands()

    assert "ollama pull qwen3:4b" in commands
    assert "python scripts/preflight.py" in commands
    assert "python scripts/evaluate_ai.py --provider-mode configured" in commands


def test_support_chat_has_initial_message_and_quick_questions():
    messages = _initial_ai_support_chat_messages()

    assert AI_SUPPORT_CHAT_KEY == "local_ai_support_chat_messages"
    assert messages == [{"role": "assistant", "content": AI_SUPPORT_WELCOME_MESSAGE, "sources": ()}]
    assert any(label == "Ollama Launch" for label, _prompt in AI_SUPPORT_QUICK_QUESTIONS)
    assert any("NaN" in prompt for _label, prompt in AI_SUPPORT_QUICK_QUESTIONS)


def test_support_chat_appends_sources_without_raw_table_data():
    messages = _initial_ai_support_chat_messages()

    _append_ai_support_chat_message(messages, "user", "Почему Wh стал NaN?")
    _append_ai_support_chat_message(
        messages,
        "assistant",
        "Проверьте C1 и C2.",
        ("config/knowledge_qa.json#wh_nan_missing_components",),
    )

    assert [message["role"] for message in messages] == ["assistant", "user", "assistant"]
    assert messages[-1]["sources"] == ("config/knowledge_qa.json#wh_nan_missing_components",)
    assert "raw" not in messages[-1]
