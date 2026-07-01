from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from ai.assistant import LocalAssistant
from ai.config_writer import (
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    configure_ollama,
)
from ai.evaluation import run_ai_evaluation
from ai.factory import build_provider
from ai.health import HttpGet, check_ai_runtime_status
from ai.knowledge_base import DocumentationKnowledgeBase
from ai.model_profiles import (
    AiModelProfile,
    find_ai_model_profile,
    load_ai_model_profile_catalog,
)
from ai.settings import load_ai_settings, local_ai_config_path


CommandRunner = Callable[[Sequence[str], int], "CommandResult"]


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass(frozen=True)
class LocalAgentSetupOptions:
    profile_id: str = "balanced"
    pull_model: bool = False
    write_config: bool = False
    run_configured_evaluation: bool = False
    base_url: str = DEFAULT_OLLAMA_BASE_URL
    timeout_seconds: int = DEFAULT_OLLAMA_TIMEOUT_SECONDS
    command_timeout_seconds: int = 1800


@dataclass(frozen=True)
class LocalAgentSetupStep:
    name: str
    status: str
    message: str


@dataclass(frozen=True)
class LocalAgentSetupReport:
    profile: AiModelProfile
    steps: tuple[LocalAgentSetupStep, ...]
    next_commands: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return all(step.status != "error" for step in self.steps)


def default_command_runner(args: Sequence[str], timeout_seconds: int) -> CommandResult:
    try:
        completed = subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        return CommandResult(returncode=127, stderr=str(exc))
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else "Command timed out."
        return CommandResult(returncode=124, stdout=stdout, stderr=stderr)

    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def build_local_agent_next_commands(profile: AiModelProfile) -> tuple[str, ...]:
    return (
        "Install Ollama from https://ollama.com/download",
        f"ollama pull {profile.model}",
        "ollama list",
        f"python scripts/setup_local_agent.py --profile {profile.id} --write-config",
        "python scripts/preflight.py",
        "python scripts/evaluate_ai.py --provider-mode configured",
        "python -m streamlit run app/streamlit_app.py",
    )


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_profile(profile_id: str, root: Path) -> AiModelProfile:
    catalog = load_ai_model_profile_catalog(root / "config" / "ai_model_profiles.json")
    profile = find_ai_model_profile(catalog, profile_id)
    if profile is None:
        known_ids = ", ".join(profile.id for profile in catalog.profiles)
        raise ValueError(f"Unknown local AI profile `{profile_id}`. Known profiles: {known_ids}")
    return profile


def _command_error_message(result: CommandResult) -> str:
    details = result.stderr.strip() or result.stdout.strip()
    return details if details else f"command exited with code {result.returncode}"


def _append_offline_evaluation_step(steps: list[LocalAgentSetupStep], root: Path) -> None:
    try:
        report = run_ai_evaluation(root=root)
    except Exception as exc:
        steps.append(
            LocalAgentSetupStep(
                name="knowledge_training_pack",
                status="error",
                message=f"Локальная RAG-база знаний не прошла проверку: {exc}",
            )
        )
        return

    steps.append(
        LocalAgentSetupStep(
            name="knowledge_training_pack",
            status="ok" if report.ok else "error",
            message=(
                f"RAG-база знаний проверена: {len(report.results)} evaluation-кейсов."
                if report.ok
                else "RAG-база знаний требует исправления перед подключением модели."
            ),
        )
    )


def _run_configured_evaluation(root: Path, config_path: Path):
    settings = load_ai_settings(config_path)
    provider = build_provider(settings)
    assistant = LocalAssistant(
        knowledge_base=DocumentationKnowledgeBase(root=root),
        provider=provider,
    )
    return run_ai_evaluation(
        root=root,
        assistant=assistant,
        provider_mode="configured",
    )


def run_local_agent_setup(
    options: LocalAgentSetupOptions | None = None,
    root: str | Path | None = None,
    config_path: str | Path | None = None,
    runner: CommandRunner = default_command_runner,
    http_get: HttpGet | None = None,
) -> LocalAgentSetupReport:
    resolved_options = options or LocalAgentSetupOptions()
    resolved_root = Path(root) if root is not None else _project_root()
    resolved_config_path = (
        Path(config_path)
        if config_path is not None
        else local_ai_config_path(resolved_root)
    )
    profile = _resolve_profile(resolved_options.profile_id, resolved_root)
    steps: list[LocalAgentSetupStep] = [
        LocalAgentSetupStep(
            name="profile",
            status="ok",
            message=(
                f"Выбран профиль {profile.id}: {profile.model}, "
                f"ориентир RAM {profile.min_ram_gb_estimate}+ GB."
            ),
        )
    ]
    next_commands = build_local_agent_next_commands(profile)

    _append_offline_evaluation_step(steps, resolved_root)

    has_action = (
        resolved_options.pull_model
        or resolved_options.write_config
        or resolved_options.run_configured_evaluation
    )
    if not has_action:
        steps.append(
            LocalAgentSetupStep(
                name="dry_run",
                status="ok",
                message="Показан план подготовки. Реальная загрузка модели запускается через --pull или --download.",
            )
        )
        return LocalAgentSetupReport(
            profile=profile,
            steps=tuple(steps),
            next_commands=next_commands,
        )

    if resolved_options.pull_model:
        version_result = runner(("ollama", "--version"), 30)
        if not version_result.ok:
            steps.append(
                LocalAgentSetupStep(
                    name="ollama_cli",
                    status="error",
                    message=(
                        "Ollama не найден. Установите Ollama, перезапустите терминал "
                        "и повторите команду подготовки."
                    ),
                )
            )
            return LocalAgentSetupReport(
                profile=profile,
                steps=tuple(steps),
                next_commands=next_commands,
            )

        steps.append(
            LocalAgentSetupStep(
                name="ollama_cli",
                status="ok",
                message=version_result.stdout.strip() or "Ollama CLI найден.",
            )
        )

        pull_result = runner(
            ("ollama", "pull", profile.model),
            resolved_options.command_timeout_seconds,
        )
        if not pull_result.ok:
            steps.append(
                LocalAgentSetupStep(
                    name="model_download",
                    status="error",
                    message=f"Не удалось скачать модель {profile.model}: {_command_error_message(pull_result)}",
                )
            )
            return LocalAgentSetupReport(
                profile=profile,
                steps=tuple(steps),
                next_commands=next_commands,
            )

        steps.append(
            LocalAgentSetupStep(
                name="model_download",
                status="ok",
                message=f"Модель {profile.model} скачана через Ollama.",
            )
        )

        list_result = runner(("ollama", "list"), 30)
        steps.append(
            LocalAgentSetupStep(
                name="model_list",
                status="ok" if list_result.ok else "error",
                message=(
                    "Локальные модели проверены через `ollama list`."
                    if list_result.ok
                    else f"Не удалось проверить `ollama list`: {_command_error_message(list_result)}"
                ),
            )
        )
        if not list_result.ok:
            return LocalAgentSetupReport(
                profile=profile,
                steps=tuple(steps),
                next_commands=next_commands,
            )

    if resolved_options.write_config:
        configure_ollama(
            resolved_config_path,
            model=profile.model,
            base_url=resolved_options.base_url,
            timeout_seconds=resolved_options.timeout_seconds,
        )
        steps.append(
            LocalAgentSetupStep(
                name="ai_config",
                status="ok",
                message=f"AI config переключен на Ollama model={profile.model}: {resolved_config_path}.",
            )
        )

    if resolved_options.write_config or resolved_options.run_configured_evaluation:
        settings = load_ai_settings(resolved_config_path)
        runtime_status = (
            check_ai_runtime_status(settings)
            if http_get is None
            else check_ai_runtime_status(settings, http_get=http_get)
        )
        steps.append(
            LocalAgentSetupStep(
                name="ai_runtime",
                status="ok" if runtime_status.ready else "error",
                message=runtime_status.message,
            )
        )
        if not runtime_status.ready:
            return LocalAgentSetupReport(
                profile=profile,
                steps=tuple(steps),
                next_commands=next_commands,
            )

    if resolved_options.run_configured_evaluation:
        configured_report = _run_configured_evaluation(
            root=resolved_root,
            config_path=resolved_config_path,
        )
        steps.append(
            LocalAgentSetupStep(
                name="configured_evaluation",
                status="ok" if configured_report.ok else "error",
                message=(
                    f"Configured AI evaluation пройден: {len(configured_report.results)} кейсов."
                    if configured_report.ok
                    else "Configured AI evaluation не прошел. Проверьте ответы локальной модели."
                ),
            )
        )

    return LocalAgentSetupReport(
        profile=profile,
        steps=tuple(steps),
        next_commands=next_commands,
    )
