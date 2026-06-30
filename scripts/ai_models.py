from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.model_profiles import (  # noqa: E402
    AiModelProfile,
    find_ai_model_profile,
    load_ai_model_profile_catalog,
    recommended_install_commands,
)


def _profile_to_dict(profile: AiModelProfile) -> dict:
    return {
        "id": profile.id,
        "title": profile.title,
        "provider": profile.provider,
        "model": profile.model,
        "min_ram_gb_estimate": profile.min_ram_gb_estimate,
        "best_for": list(profile.best_for),
        "notes": profile.notes,
    }


def _print_profile(profile: AiModelProfile) -> None:
    print(f"{profile.id}: {profile.title}")
    print(f"  provider: {profile.provider}")
    print(f"  model: {profile.model}")
    print(f"  estimated RAM: {profile.min_ram_gb_estimate}+ GB")
    print("  best for: " + ", ".join(profile.best_for))
    print(f"  notes: {profile.notes}")
    print("  commands:")
    for command in recommended_install_commands(profile):
        print(f"    {command}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="List local AI model profiles.")
    parser.add_argument("--profile", help="Show one profile by id.")
    parser.add_argument("--json", action="store_true", help="Print catalog as JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    catalog = load_ai_model_profile_catalog()
    profiles = catalog.profiles

    if args.profile:
        profile = find_ai_model_profile(catalog, args.profile)
        if profile is None:
            known_ids = ", ".join(profile.id for profile in profiles)
            parser.error(f"unknown profile `{args.profile}`. Known profiles: {known_ids}")

        if args.json:
            print(json.dumps(_profile_to_dict(profile), ensure_ascii=False, indent=2))
        else:
            _print_profile(profile)
        return 0

    if args.json:
        print(
            json.dumps(
                {
                    "version": catalog.version,
                    "source": catalog.source,
                    "source_urls": list(catalog.source_urls),
                    "profiles": [_profile_to_dict(profile) for profile in profiles],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print(f"Local AI model profiles ({catalog.version})")
    print(catalog.source)
    print("")
    for profile in profiles:
        _print_profile(profile)
        print("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
