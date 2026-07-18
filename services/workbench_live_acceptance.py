"""Automated live acceptance for the production Streamlit Workbench.

The runner combines two complementary checks:

* a real temporary Streamlit server process and its health endpoint;
* Streamlit's official ``AppTest`` runtime for deterministic UI interaction.

This avoids treating a static import or an HTTP 200 response as proof that the
Workbench script actually renders without a traceback.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable
from urllib.error import URLError
from urllib.request import urlopen

from core.build_info import BUILD_CHANNEL, BUILD_VERSION, PROJECT_ROOT, runtime_build_info

ACCEPTANCE_SCHEMA = "gas-ratio-pro/live-workbench-acceptance/v1"
REQUIRED_MENU_KEYS = (
    "workbench_menu_файл",
    "workbench_menu_проект",
    "workbench_menu_данные",
    "workbench_menu_las",
    "workbench_menu_корреляция",
    "workbench_menu_интерпретация",
    "workbench_menu_отчёты",
    "workbench_menu_экспорт",
    "workbench_menu_настройки",
    "workbench_menu_справка",
)

LOCALIZED_WORKBENCH_CONTRACTS: dict[str, dict[str, object]] = {
    "ru": {
        "menus": ("Файл", "Проект", "Данные", "LAS", "Корреляция", "Интерпретация", "Отчёты", "Экспорт", "Настройки", "Справка"),
        "explorer": "Проводник проекта",
        "properties": "Свойства",
        "status_aria": "Строка состояния",
    },
    "kk": {
        "menus": ("Файл", "Жоба", "Деректер", "LAS", "Корреляция", "Интерпретация", "Есептер", "Экспорт", "Баптаулар", "Анықтама"),
        "explorer": "Жоба навигаторы",
        "properties": "Қасиеттер",
        "status_aria": "Күй жолағы",
    },
    "en": {
        "menus": ("File", "Project", "Data", "LAS", "Correlation", "Interpretation", "Reports", "Export", "Settings", "Help"),
        "explorer": "Project Explorer",
        "properties": "Properties",
        "status_aria": "Status bar",
    },
}


@dataclass(frozen=True, slots=True)
class AcceptanceCheck:
    check_id: str
    passed: bool
    summary: str
    evidence: dict[str, Any]


@dataclass(frozen=True, slots=True)
class LiveWorkbenchAcceptanceReport:
    schema: str
    acceptance_id: str
    started_at_utc: str
    finished_at_utc: str
    build_version: str
    build_channel: str
    project_root: str
    entry_point: str
    entry_point_sha256: str
    python_version: str
    streamlit_version: str
    server_port: int
    checks: tuple[AcceptanceCheck, ...]

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["passed"] = self.passed
        payload["checks_passed"] = sum(1 for check in self.checks if check.passed)
        payload["checks_total"] = len(self.checks)
        return payload

    def write_json(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return destination


class LiveWorkbenchAcceptanceError(RuntimeError):
    """Raised when the acceptance runner cannot complete its infrastructure step."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _element_keys(elements: Iterable[Any]) -> set[str]:
    keys: set[str] = set()
    for element in elements:
        key = getattr(element, "key", None)
        if key:
            keys.add(str(key))
    return keys


def _markdown_values(app_test: Any) -> tuple[str, ...]:
    return tuple(str(item.value) for item in app_test.markdown)


def _contains(markdown_values: Iterable[str], fragment: str) -> bool:
    return any(fragment in value for value in markdown_values)


def _exceptions(app_test: Any) -> tuple[str, ...]:
    return tuple(str(item.value) for item in app_test.exception)


class LiveWorkbenchAcceptanceRunner:
    """Run stable-promotion acceptance against one extracted project tree."""

    def __init__(
        self,
        project_root: str | Path = PROJECT_ROOT,
        *,
        port: int | None = None,
        startup_timeout_seconds: float = 60.0,
        app_timeout_seconds: float = 120.0,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.entry_point = (self.project_root / "app" / "streamlit_app.py").resolve()
        self.port = int(port or _free_port())
        self.startup_timeout_seconds = float(startup_timeout_seconds)
        self.app_timeout_seconds = float(app_timeout_seconds)

    def run(self) -> LiveWorkbenchAcceptanceReport:
        started = _utc_now()
        checks: list[AcceptanceCheck] = []
        log_file = tempfile.NamedTemporaryFile(
            mode="w+", encoding="utf-8", prefix="gas-ratio-pro-live-", suffix=".log", delete=False
        )
        log_path = Path(log_file.name)
        process: subprocess.Popen[str] | None = None
        try:
            process = self._start_server(log_file)
            health_evidence = self._wait_for_health(process, log_path)
            checks.append(AcceptanceCheck("server.health", True, "Temporary Streamlit server is healthy.", health_evidence))

            app_test, streamlit_version = self._run_app_test()
            checks.extend(self._inspect_initial_workbench(app_test))
            checks.extend(self._inspect_localized_workbench())
            checks.extend(self._exercise_las_command(app_test))
        except Exception as exc:
            checks.append(
                AcceptanceCheck(
                    "acceptance.runner",
                    False,
                    f"Acceptance runner failed: {type(exc).__name__}: {exc}",
                    {"server_log_tail": self._log_tail(log_path)},
                )
            )
            try:
                import streamlit

                streamlit_version = str(streamlit.__version__)
            except Exception:
                streamlit_version = "unavailable"
        finally:
            if process is not None:
                self._stop_server(process)
            log_file.close()
            try:
                log_path.unlink(missing_ok=True)
            except OSError:
                pass

        info = runtime_build_info()
        finished = _utc_now()
        acceptance_seed = "|".join(
            [str(info.version), str(info.channel), str(self.entry_point), started, finished]
        ).encode("utf-8")
        report = LiveWorkbenchAcceptanceReport(
            schema=ACCEPTANCE_SCHEMA,
            acceptance_id="lwa-" + hashlib.sha256(acceptance_seed).hexdigest()[:16],
            started_at_utc=started,
            finished_at_utc=finished,
            build_version=str(info.version),
            build_channel=str(info.channel),
            project_root=str(self.project_root),
            entry_point=str(self.entry_point),
            entry_point_sha256=_sha256(self.entry_point),
            python_version=platform.python_version(),
            streamlit_version=streamlit_version,
            server_port=self.port,
            checks=tuple(checks),
        )
        return report

    def _start_server(self, log_file: Any) -> subprocess.Popen[str]:
        if not self.entry_point.is_file():
            raise LiveWorkbenchAcceptanceError(f"entry point not found: {self.entry_point}")
        env = os.environ.copy()
        env["GAS_RATIO_PRO_LEGACY_UI"] = ""
        env["GAS_RATIO_PRO_DIAGNOSTICS"] = "1"
        env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
        command = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(self.entry_point),
            "--server.port",
            str(self.port),
            "--server.address",
            "127.0.0.1",
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ]
        return subprocess.Popen(
            command,
            cwd=self.project_root,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )

    def _wait_for_health(self, process: subprocess.Popen[str], log_path: Path) -> dict[str, Any]:
        deadline = time.monotonic() + self.startup_timeout_seconds
        url = f"http://127.0.0.1:{self.port}/_stcore/health"
        last_error = ""
        while time.monotonic() < deadline:
            exit_code = process.poll()
            if exit_code is not None:
                raise LiveWorkbenchAcceptanceError(
                    f"Streamlit process exited with code {exit_code}; log: {self._log_tail(log_path)}"
                )
            try:
                with urlopen(url, timeout=2.0) as response:  # noqa: S310 - loopback acceptance endpoint
                    body = response.read().decode("utf-8", errors="replace").strip()
                    if response.status == 200 and body.casefold() == "ok":
                        return {
                            "url": url,
                            "status": response.status,
                            "body": body,
                            "pid": process.pid,
                        }
            except (OSError, URLError) as exc:
                last_error = str(exc)
            time.sleep(0.25)
        raise LiveWorkbenchAcceptanceError(
            f"Streamlit health timeout ({last_error}); log: {self._log_tail(log_path)}"
        )

    def _run_app_test(self, locale: str | None = None) -> tuple[Any, str]:
        from streamlit import __version__ as streamlit_version
        from streamlit.testing.v1 import AppTest

        app_test = AppTest.from_file(str(self.entry_point), default_timeout=self.app_timeout_seconds)
        if locale is not None:
            app_test.session_state["user_settings.interface_language"] = locale
        app_test.run(timeout=self.app_timeout_seconds)
        return app_test, str(streamlit_version)

    def _inspect_initial_workbench(self, app_test: Any) -> list[AcceptanceCheck]:
        markdown = _markdown_values(app_test)
        button_keys = _element_keys(app_test.button)
        text_input_keys = _element_keys(app_test.text_input)
        runtime = runtime_build_info()
        badge = __import__("app.workbench_renderer", fromlist=["workbench_build_badge"]).workbench_build_badge()
        exceptions = _exceptions(app_test)

        checks = [
            AcceptanceCheck(
                "runtime.no_traceback",
                not exceptions,
                "Initial Workbench render has no Streamlit exception." if not exceptions else "Initial Workbench render raised an exception.",
                {"exceptions": list(exceptions)},
            ),
            AcceptanceCheck(
                "runtime.identity",
                runtime.version == BUILD_VERSION
                and runtime.channel == BUILD_CHANNEL
                and Path(runtime.project_root).resolve() == self.project_root
                and Path(runtime.entry_point).resolve() == self.entry_point
                and badge == runtime.to_dict(),
                "Build badge and runtime identity point to the active extracted source tree.",
                {"runtime": runtime.to_dict(), "badge": badge},
            ),
            AcceptanceCheck(
                "workbench.toolbar",
                set(REQUIRED_MENU_KEYS).issubset(button_keys),
                "Top toolbar exposes all required command-backed menus.",
                {"required_keys": list(REQUIRED_MENU_KEYS), "visible_keys": sorted(button_keys)},
            ),
            AcceptanceCheck(
                "workbench.project_explorer",
                _contains(markdown, "workbench-pane-title'><span>Проводник проекта")
                and "workbench_project_explorer_search" in text_input_keys,
                "Project Explorer and its search control are visible.",
                {"search_key_present": "workbench_project_explorer_search" in text_input_keys},
            ),
            AcceptanceCheck(
                "workbench.workspace_host",
                _contains(markdown, "workbench-workspace-context")
                and _contains(markdown, "nav.dashboard"),
                "Workspace Host renders the dashboard route.",
                {"route": "nav.dashboard"},
            ),
            AcceptanceCheck(
                "workbench.properties",
                _contains(markdown, "workbench-pane-title'><span>Свойства")
                and _contains(markdown, "workbench-property"),
                "Properties pane renders a selection-aware model.",
                {},
            ),
            AcceptanceCheck(
                "workbench.status_bar",
                _contains(markdown, "workbench-statusbar")
                and _contains(markdown, "workbench-status-ready"),
                "Status Bar renders readiness and active context.",
                {},
            ),
        ]
        return checks

    def _inspect_localized_workbench(self) -> list[AcceptanceCheck]:
        checks: list[AcceptanceCheck] = []
        for locale, contract in LOCALIZED_WORKBENCH_CONTRACTS.items():
            app_test, _ = self._run_app_test(locale=locale)
            markdown = _markdown_values(app_test)
            labels = {str(item.label) for item in app_test.button[:10]}
            expected_menus = set(contract["menus"])
            exceptions = _exceptions(app_test)
            explorer = str(contract["explorer"])
            properties = str(contract["properties"])
            status_aria = str(contract["status_aria"])
            passed = (
                not exceptions
                and expected_menus.issubset(labels)
                and _contains(markdown, f"<span>{explorer}</span>")
                and _contains(markdown, f"<span>{properties}</span>")
                and _contains(markdown, f"aria-label='{status_aria}'")
                and _contains(markdown, BUILD_VERSION)
            )
            checks.append(
                AcceptanceCheck(
                    f"i18n.{locale}",
                    passed,
                    f"Workbench renders its primary stable regions in locale {locale}.",
                    {
                        "locale": locale,
                        "expected_menus": sorted(expected_menus),
                        "visible_menus": sorted(labels),
                        "explorer": explorer,
                        "properties": properties,
                        "status_aria": status_aria,
                        "exceptions": list(exceptions),
                    },
                )
            )
        return checks

    def _exercise_las_command(self, app_test: Any) -> list[AcceptanceCheck]:
        las_button = next((item for item in app_test.button if str(item.key) == "workbench_menu_las"), None)
        if las_button is None:
            return [AcceptanceCheck("command.las", False, "LAS command button is not available.", {})]
        las_button.click().run(timeout=self.app_timeout_seconds)
        markdown = _markdown_values(app_test)
        exceptions = _exceptions(app_test)
        button_keys = _element_keys(app_test.button)
        checks = [
            AcceptanceCheck(
                "command.las",
                not exceptions
                and _contains(markdown, "workbench-command-feedback")
                and _contains(markdown, "nav.las_workspace"),
                "LAS toolbar command executes and selects the LAS workspace route.",
                {"exceptions": list(exceptions), "route": "nav.las_workspace"},
            ),
            AcceptanceCheck(
                "las_viewer.runtime",
                not exceptions
                and _contains(markdown, "workbench-pane-title'><span>LAS Viewer")
                and _contains(markdown, "<strong>Module:</strong> LAS Viewer")
                and "las_workspace_open_default" in button_keys,
                "LAS Viewer renders without a traceback and exposes its workspace action.",
                {"open_action_present": "las_workspace_open_default" in button_keys},
            ),
        ]
        open_button = next((item for item in app_test.button if str(item.key) == "las_workspace_open_default"), None)
        if open_button is not None:
            open_button.click().run(timeout=self.app_timeout_seconds)
            open_exceptions = _exceptions(app_test)
            checks.append(
                AcceptanceCheck(
                    "las_viewer.open_action",
                    not open_exceptions,
                    "LAS Workspace open action completes without a traceback.",
                    {"exceptions": list(open_exceptions)},
                )
            )
        return checks

    @staticmethod
    def _log_tail(path: Path, *, max_chars: int = 4000) -> str:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        return content[-max_chars:]

    @staticmethod
    def _stop_server(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
