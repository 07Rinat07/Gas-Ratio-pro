from pathlib import Path

from services.plugin_manager_service import PluginManagerService


def test_plugin_manager_service_registers_manifest_and_registry(tmp_path: Path) -> None:
    service = PluginManagerService(tmp_path)
    project_id = "demo-project"
    manifest = service.manifest_template("Custom Importer", plugin_id="custom-importer", extension_points=("data.importer",))

    registered = service.register(project_id, manifest)
    enabled = service.enable(project_id, registered.id)
    registry = service.registry(project_id)

    assert enabled.status == "enabled"
    assert registered.id == "custom-importer"
    assert service.summary(project_id).plugins == 1
    assert registry["plugins"][0]["id"] == "custom-importer"
