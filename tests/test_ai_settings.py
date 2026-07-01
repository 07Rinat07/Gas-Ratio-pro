from __future__ import annotations

from ai.settings import local_ai_config_path, resolve_ai_config_path


def test_resolve_ai_config_path_prefers_local_override(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    tracked_config = config_dir / "ai.json"
    local_config = config_dir / "ai.local.json"
    tracked_config.write_text("{}", encoding="utf-8")

    assert resolve_ai_config_path(tmp_path) == tracked_config

    local_config.write_text("{}", encoding="utf-8")

    assert local_ai_config_path(tmp_path) == local_config
    assert resolve_ai_config_path(tmp_path) == local_config