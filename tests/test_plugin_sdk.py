from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from projects.plugin_sdk import (
    PLUGIN_SDK_SCHEMA,
    build_plugin_api_registry,
    build_plugin_hook_table,
    build_plugin_table,
    build_plugin_validation_table,
    create_plugin_manifest_template,
    create_plugin_scaffold,
    delete_plugin,
    export_plugin_manifest_json,
    get_plugin,
    import_plugin_manifest_json,
    list_plugin_hooks,
    list_plugins,
    register_plugin,
    register_plugin_hook,
    summarize_plugin_sdk,
    update_plugin_status,
    validate_plugin_manifest,
)


def test_plugin_manifest_template_validation_and_json_roundtrip() -> None:
    manifest_payload = create_plugin_manifest_template(
        "Gas Ratio Dashboard Card",
        plugin_id="gas-card",
        extension_points=["dashboard.card"],
    )

    assert manifest_payload["schema"] == PLUGIN_SDK_SCHEMA
    assert manifest_payload["id"] == "gas-card"
    assert validate_plugin_manifest(manifest_payload) == ()

    exported = export_plugin_manifest_json(manifest_payload)
    imported = import_plugin_manifest_json(exported)
    assert imported.id == "gas-card"
    assert imported.extension_points == ("dashboard.card",)


def test_register_list_status_and_delete_plugin(tmp_path: Path) -> None:
    plugin = register_plugin(
        tmp_path,
        "demo_project",
        {
            "id": "quality-rule",
            "name": "Quality Rule Plugin",
            "version": "0.2.0",
            "permissions": ["read:project", "read:las"],
            "extension_points": ["quality.rule"],
        },
    )

    assert get_plugin(tmp_path, "demo_project", plugin.id).name == "Quality Rule Plugin"
    assert len(list_plugins(tmp_path, "demo_project")) == 1

    enabled = update_plugin_status(tmp_path, "demo_project", plugin.id, "enabled")
    assert enabled.status == "enabled"
    assert list_plugins(tmp_path, "demo_project", status="enabled")[0].id == plugin.id

    assert delete_plugin(tmp_path, "demo_project", plugin.id) is True
    assert list_plugins(tmp_path, "demo_project") == ()


def test_invalid_manifest_is_rejected() -> None:
    issues = validate_plugin_manifest(
        {
            "id": "bad",
            "name": "Bad Plugin",
            "version": "0.1.0",
            "entry_point": "plugin.txt",
            "permissions": ["root:everything"],
            "extension_points": ["unknown.point"],
            "status": "draft",
        }
    )
    codes = {issue.code for issue in issues}
    assert "unknown_permission" in codes
    assert "unknown_extension_point" in codes
    assert "invalid_entry_point" in codes

    table = build_plugin_validation_table(issues)
    assert isinstance(table, pd.DataFrame)
    assert set(table["Код"]) == codes


def test_hooks_registry_and_tables(tmp_path: Path) -> None:
    plugin = register_plugin(
        tmp_path,
        "p1",
        {
            "id": "report-renderer",
            "name": "Report Renderer",
            "version": "1.0.0",
            "permissions": ["read:reports", "write:reports"],
            "extension_points": ["report.block.renderer"],
            "status": "draft",
        },
    )
    update_plugin_status(tmp_path, "p1", plugin.id, "enabled")
    hook = register_plugin_hook(
        tmp_path,
        "p1",
        {"plugin_id": plugin.id, "event": "report.exported", "handler": "plugin:on_report_exported", "priority": 10},
    )

    hooks = list_plugin_hooks(tmp_path, "p1", event="report.exported")
    assert hooks == (hook,)

    registry = build_plugin_api_registry(list_plugins(tmp_path, "p1"), hooks)
    assert registry["schema"] == PLUGIN_SDK_SCHEMA
    assert registry["extension_points"]["report.block.renderer"] == [plugin.id]
    assert registry["hooks"][0]["event"] == "report.exported"

    plugins_table = build_plugin_table(list_plugins(tmp_path, "p1"))
    hooks_table = build_plugin_hook_table(hooks)
    assert plugins_table.loc[0, "Статус"] == "enabled"
    assert hooks_table.loc[0, "Priority"] == 10


def test_scaffold_and_summary(tmp_path: Path) -> None:
    plugin_dir = create_plugin_scaffold(tmp_path, "Custom Importer", plugin_id="custom-importer", extension_points=["data.importer"])
    assert (plugin_dir / "plugin.json").exists()
    assert (plugin_dir / "plugin.py").exists()

    manifest = import_plugin_manifest_json((plugin_dir / "plugin.json").read_text(encoding="utf-8"))
    register_plugin(tmp_path, "p2", manifest)
    summary = summarize_plugin_sdk(tmp_path, "p2")
    assert summary.plugins == 1
    assert "data.importer" in summary.extension_points
    assert "read:project" in summary.permissions


def test_register_hook_requires_existing_plugin(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        register_plugin_hook(tmp_path, "missing", {"plugin_id": "none", "event": "project.opened", "handler": "plugin:open"})
