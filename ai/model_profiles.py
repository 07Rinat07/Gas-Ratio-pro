from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AiModelProfile:
    id: str
    title: str
    provider: str
    model: str
    min_ram_gb_estimate: int
    best_for: tuple[str, ...]
    notes: str


@dataclass(frozen=True)
class AiModelProfileCatalog:
    version: str
    source: str
    source_urls: tuple[str, ...]
    profiles: tuple[AiModelProfile, ...]


def default_ai_model_profiles_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "ai_model_profiles.json"


def _read_non_empty_string(raw: dict, key: str) -> str:
    value = str(raw.get(key, "")).strip()
    if not value:
        raise ValueError(f"AI model profile field `{key}` must be a non-empty string.")
    return value


def _read_positive_int(raw: dict, key: str) -> int:
    try:
        value = int(raw.get(key))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"AI model profile field `{key}` must be a positive integer.") from exc

    if value <= 0:
        raise ValueError(f"AI model profile field `{key}` must be a positive integer.")
    return value


def _read_string_tuple(value: object, key: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"AI model profile field `{key}` must be a list.")

    items = tuple(str(item).strip() for item in value if str(item).strip())
    if not items:
        raise ValueError(f"AI model profile field `{key}` must contain at least one item.")
    return items


def _parse_profile(raw_profile: object) -> AiModelProfile:
    if not isinstance(raw_profile, dict):
        raise ValueError("AI model profile entry must be an object.")

    provider = _read_non_empty_string(raw_profile, "provider")
    if provider != "ollama":
        raise ValueError(f"Unsupported AI model profile provider: {provider}")

    return AiModelProfile(
        id=_read_non_empty_string(raw_profile, "id"),
        title=_read_non_empty_string(raw_profile, "title"),
        provider=provider,
        model=_read_non_empty_string(raw_profile, "model"),
        min_ram_gb_estimate=_read_positive_int(raw_profile, "min_ram_gb_estimate"),
        best_for=_read_string_tuple(raw_profile.get("best_for"), "best_for"),
        notes=_read_non_empty_string(raw_profile, "notes"),
    )


def load_ai_model_profile_catalog(path: str | Path | None = None) -> AiModelProfileCatalog:
    config_path = Path(path) if path is not None else default_ai_model_profiles_path()
    with config_path.open("r", encoding="utf-8") as file:
        raw_catalog = json.load(file)

    if not isinstance(raw_catalog, dict):
        raise ValueError("AI model profile catalog root must be an object.")

    raw_profiles = raw_catalog.get("profiles")
    if not isinstance(raw_profiles, list) or not raw_profiles:
        raise ValueError("AI model profile catalog must contain a non-empty `profiles` list.")

    profiles = tuple(_parse_profile(raw_profile) for raw_profile in raw_profiles)
    profile_ids = [profile.id for profile in profiles]
    duplicate_ids = sorted({profile_id for profile_id in profile_ids if profile_ids.count(profile_id) > 1})
    if duplicate_ids:
        raise ValueError("Duplicate AI model profile ids: " + ", ".join(duplicate_ids))

    source_urls = _read_string_tuple(raw_catalog.get("source_urls"), "source_urls")
    return AiModelProfileCatalog(
        version=_read_non_empty_string(raw_catalog, "version"),
        source=_read_non_empty_string(raw_catalog, "source"),
        source_urls=source_urls,
        profiles=profiles,
    )


def find_ai_model_profile(
    catalog: AiModelProfileCatalog,
    profile_id: str,
) -> AiModelProfile | None:
    requested_id = profile_id.strip()
    for profile in catalog.profiles:
        if profile.id == requested_id:
            return profile
    return None


def recommended_install_commands(profile: AiModelProfile) -> tuple[str, ...]:
    return (
        f"ollama pull {profile.model}",
        "ollama list",
        "python scripts/preflight.py",
    )
