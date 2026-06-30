from __future__ import annotations

import json

import pytest

from ai.model_profiles import (
    find_ai_model_profile,
    load_ai_model_profile_catalog,
    recommended_install_commands,
)


def test_default_ai_model_profile_catalog_loads():
    catalog = load_ai_model_profile_catalog()

    assert catalog.version
    assert "ollama.com/library" in " ".join(catalog.source_urls)
    assert find_ai_model_profile(catalog, "balanced") is not None
    assert all(profile.provider == "ollama" for profile in catalog.profiles)


def test_ai_model_profile_recommended_commands_include_model():
    catalog = load_ai_model_profile_catalog()
    profile = find_ai_model_profile(catalog, "balanced")

    assert profile is not None
    commands = recommended_install_commands(profile)

    assert commands[0] == f"ollama pull {profile.model}"
    assert "preflight" in commands[-1]


def test_ai_model_profile_catalog_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text(
        json.dumps(
            {
                "version": "test",
                "source": "test",
                "source_urls": ["https://example.test"],
                "profiles": [
                    {
                        "id": "same",
                        "title": "A",
                        "provider": "ollama",
                        "model": "model-a",
                        "min_ram_gb_estimate": 8,
                        "best_for": ["test"],
                        "notes": "test",
                    },
                    {
                        "id": "same",
                        "title": "B",
                        "provider": "ollama",
                        "model": "model-b",
                        "min_ram_gb_estimate": 12,
                        "best_for": ["test"],
                        "notes": "test",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate"):
        load_ai_model_profile_catalog(path)


def test_ai_model_profile_catalog_rejects_invalid_provider(tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text(
        json.dumps(
            {
                "version": "test",
                "source": "test",
                "source_urls": ["https://example.test"],
                "profiles": [
                    {
                        "id": "cloud",
                        "title": "Cloud",
                        "provider": "cloud-api",
                        "model": "external-model",
                        "min_ram_gb_estimate": 8,
                        "best_for": ["test"],
                        "notes": "test",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported AI model profile provider"):
        load_ai_model_profile_catalog(path)
