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
)
from ai.local_agent_setup import (  # noqa: E402
    LocalAgentSetupOptions,
    LocalAgentSetupReport,
    run_local_agent_setup,
)


def _report_to_dict(report: LocalAgentSetupReport) -> dict:
    return {
        "ok": report.ok,
        "profile": {
            "id": report.profile.id,
            "model": report.profile.model,
            "title": report.profile.title,
            "min_ram_gb_estimate": report.profile.min_ram_gb_estimate,
        },
        "steps": [
            {
                "name": step.name,
                "status": step.status,
                "message": step.message,
            }
            for step in report.steps
        ],
        "next_commands": list(report.next_commands),
    }


def _print_report(report: LocalAgentSetupReport) -> None:
    print(f"Local AI agent setup profile: {report.profile.id} ({report.profile.model})")
    print("")
    for step in report.steps:
        print(f"[{step.status}] {step.name}: {step.message}")
    print("")
    print("Next commands:")
    for command in report.next_commands:
        print(f"  {command}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare the free local AI agent runtime with Ollama and the project RAG knowledge base."
    )
    parser.add_argument("--profile", default="balanced", help="Local model profile id.")
    parser.add_argument("--config", default=str(PROJECT_ROOT / "config" / "ai.json"), help="Path to config/ai.json.")
    parser.add_argument(
        "--pull",
        dest="pull_model",
        action="store_true",
        help="Download the selected model with `ollama pull`.",
    )
    parser.add_argument(
        "--download",
        dest="pull_model",
        action="store_true",
        help="Alias for --pull.",
    )
    parser.add_argument(
        "--write-config",
        action="store_true",
        help="Switch config/ai.json to Ollama with the selected profile.",
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Run configured AI evaluation after the local model is ready.",
    )
    parser.add_argument("--base-url", default=DEFAULT_OLLAMA_BASE_URL, help="Ollama base URL.")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_OLLAMA_TIMEOUT_SECONDS,
        help="Ollama HTTP timeout for config/ai.json.",
    )
    parser.add_argument(
        "--command-timeout-seconds",
        type=int,
        default=1800,
        help="Timeout for long Ollama CLI commands.",
    )
    parser.add_argument("--json", action="store_true", help="Print setup report as JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    options = LocalAgentSetupOptions(
        profile_id=args.profile,
        pull_model=args.pull_model,
        write_config=args.write_config,
        run_configured_evaluation=args.evaluate,
        base_url=args.base_url,
        timeout_seconds=args.timeout_seconds,
        command_timeout_seconds=args.command_timeout_seconds,
    )
    report = run_local_agent_setup(
        options=options,
        root=PROJECT_ROOT,
        config_path=args.config,
    )

    if args.json:
        print(json.dumps(_report_to_dict(report), ensure_ascii=False, indent=2))
    else:
        _print_report(report)

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
