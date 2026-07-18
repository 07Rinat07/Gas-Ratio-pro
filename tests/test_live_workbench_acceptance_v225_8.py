from __future__ import annotations

import json
from pathlib import Path

from core.build_info import BUILD_CHANNEL, BUILD_VERSION, PROJECT_ROOT
from services.workbench_live_acceptance import (
    ACCEPTANCE_SCHEMA,
    LiveWorkbenchAcceptanceReport,
    LiveWorkbenchAcceptanceRunner,
)


def test_acceptance_contract_declares_all_stable_promotion_checks() -> None:
    contract = json.loads((PROJECT_ROOT / "config" / "live_workbench_acceptance_contract_v225_8.json").read_text(encoding="utf-8"))
    assert contract["version"] == BUILD_VERSION
    assert contract["required_channel"] == "stable"
    assert contract["checks"] == [
        "server.health",
        "runtime.no_traceback",
        "runtime.identity",
        "workbench.toolbar",
        "workbench.project_explorer",
        "workbench.workspace_host",
        "workbench.properties",
        "workbench.status_bar",
        "i18n.ru",
        "i18n.kk",
        "i18n.en",
        "command.las",
        "las_viewer.runtime",
        "las_viewer.open_action",
    ]
    assert all(contract["promotion_policy"].values())


def test_live_acceptance_executes_real_server_and_streamlit_runtime(tmp_path: Path) -> None:
    report = LiveWorkbenchAcceptanceRunner(
        PROJECT_ROOT,
        startup_timeout_seconds=60,
        app_timeout_seconds=120,
    ).run()
    output = report.write_json(tmp_path / "acceptance.json")
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert report.schema == ACCEPTANCE_SCHEMA
    assert report.build_version == BUILD_VERSION
    assert report.build_channel == BUILD_CHANNEL == "stable"
    assert Path(report.project_root) == PROJECT_ROOT.resolve()
    assert Path(report.entry_point) == (PROJECT_ROOT / "app" / "streamlit_app.py").resolve()
    assert len(report.entry_point_sha256) == 64
    assert report.passed is True
    assert payload["passed"] is True
    assert payload["checks_passed"] == payload["checks_total"] == 14
    assert [check.check_id for check in report.checks] == [
        "server.health",
        "runtime.no_traceback",
        "runtime.identity",
        "workbench.toolbar",
        "workbench.project_explorer",
        "workbench.workspace_host",
        "workbench.properties",
        "workbench.status_bar",
        "i18n.ru",
        "i18n.kk",
        "i18n.en",
        "command.las",
        "las_viewer.runtime",
        "las_viewer.open_action",
    ]


def test_acceptance_report_fails_when_any_check_fails() -> None:
    from services.workbench_live_acceptance import AcceptanceCheck

    report = LiveWorkbenchAcceptanceReport(
        schema=ACCEPTANCE_SCHEMA,
        acceptance_id="lwa-test",
        started_at_utc="2026-07-18T00:00:00Z",
        finished_at_utc="2026-07-18T00:00:01Z",
        build_version="v225.8",
        build_channel="stable",
        project_root=str(PROJECT_ROOT),
        entry_point=str(PROJECT_ROOT / "app" / "streamlit_app.py"),
        entry_point_sha256="0" * 64,
        python_version="3.13",
        streamlit_version="1.59",
        server_port=8501,
        checks=(AcceptanceCheck("demo", False, "failure", {}),),
    )
    assert report.passed is False
    assert report.to_dict()["checks_passed"] == 0
