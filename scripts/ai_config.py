from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.config_writer import (  # noqa: E402
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    build_offline_docs_config,
    build_ollama_config,
    configure_offline_docs,
    configure_ollama,
    read_ai_config_document,
)
from ai.model_profiles import find_ai_model_profile, load_ai_model_profile_catalog  # noqa: E402
from ai.settings import load_ai_settings  # noqa: E402


DEFAULT_AI_CONFIG = PROJECT_ROOT / "config" / "ai.json"


def _print_config(config: dict) -> None:
    print(json.dumps(config, ensure_ascii=False, indent=2))


def _resolve_model(model: str | None, profile_id: str | None) -> str:
    if model:
        return model
    if not profile_id:
        raise ValueError("Either --model or --profile is required for ollama mode.")

    catalog = load_ai_model_profile_catalog()
    profile = find_ai_model_profile(catalog, profile_id)
    if profile is None:
        known_ids = ", ".join(profile.id for profile in catalog.profiles)
        raise ValueError(f"Unknown AI model profile `{profile_id}`. Known profiles: {known_ids}")
    return profile.model


def _print_next_steps(provider: str) -> None:
    print("")
    print("Next checks:")
    print("  python scripts/preflight.py")
    print("  python scripts/evaluate_ai.py")
    if provider == "ollama":
        print("  python scripts/evaluate_ai.py --provider-mode configured")


def _status(args: argparse.Namespace) -> int:
    settings = load_ai_settings(args.config)
    print(f"provider: {settings.provider}")
    print(f"privacy.send_full_table: {settings.privacy.send_full_table}")
    print(f"privacy.send_selected_interval_only: {settings.privacy.send_selected_interval_only}")
    print(f"ollama.base_url: {settings.ollama.base_url}")
    print(f"ollama.model: {settings.ollama.model or '-'}")
    print(f"ollama.timeout_seconds: {settings.ollama.timeout_seconds}")
    return 0


def _offline_docs(args: argparse.Namespace) -> int:
    current_config = read_ai_config_document(args.config)
    config = build_offline_docs_config(current_config)
    if args.write:
        configure_offline_docs(args.config)
        print(f"Updated {args.config}: provider=offline-docs")
        _print_next_steps("offline-docs")
        return 0

    print("Preview only. Add --write to update config/ai.json.")
    _print_config(config)
    return 0


def _ollama(args: argparse.Namespace) -> int:
    model = _resolve_model(args.model, args.profile)
    current_config = read_ai_config_document(args.config)
    config = build_ollama_config(
        model=model,
        existing_config=current_config,
        base_url=args.base_url,
        timeout_seconds=args.timeout_seconds,
    )
    if args.write:
        configure_ollama(
            args.config,
            model=model,
            base_url=args.base_url,
            timeout_seconds=args.timeout_seconds,
        )
        print(f"Updated {args.config}: provider=ollama, model={model}")
        print("")
        print("Before using Ollama, make sure the model exists locally:")
        print(f"  ollama pull {model}")
        print("  ollama list")
        _print_next_steps("ollama")
        return 0

    print("Preview only. Add --write to update config/ai.json.")
    _print_config(config)
    print("")
    print("Model preparation:")
    print(f"  ollama pull {model}")
    print("  ollama list")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect or update local AI provider config.")
    parser.add_argument("--config", type=Path, default=DEFAULT_AI_CONFIG, help="Path to config/ai.json.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Show current AI config.")
    status_parser.set_defaults(func=_status)

    offline_parser = subparsers.add_parser("offline-docs", help="Switch provider to offline-docs.")
    offline_parser.add_argument("--write", action="store_true", help="Write config/ai.json.")
    offline_parser.set_defaults(func=_offline_docs)

    ollama_parser = subparsers.add_parser("ollama", help="Switch provider to Ollama.")
    model_group = ollama_parser.add_mutually_exclusive_group(required=True)
    model_group.add_argument("--model", help="Exact local Ollama model name.")
    model_group.add_argument("--profile", help="Model profile id from config/ai_model_profiles.json.")
    ollama_parser.add_argument("--base-url", default=DEFAULT_OLLAMA_BASE_URL, help="Ollama base URL.")
    ollama_parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_OLLAMA_TIMEOUT_SECONDS,
        help="Ollama request timeout.",
    )
    ollama_parser.add_argument("--write", action="store_true", help="Write config/ai.json.")
    ollama_parser.set_defaults(func=_ollama)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ValueError as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
