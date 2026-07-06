from core.workspace_infrastructure import (
    ConfigurationManager,
    LoggingCenter,
    NotificationCenter,
    NotificationLevel,
    ServiceRegistry,
    TaskManager,
    TaskStatus,
    WorkspaceConfiguration,
    WorkspaceSettings,
    build_default_workspace_services,
)


def test_configuration_manager_saves_loads_and_backups(tmp_path):
    manager = ConfigurationManager(tmp_path)
    config = WorkspaceConfiguration(
        name="main project",
        settings=WorkspaceSettings(theme="invalid", autosave_interval_minutes=0, default_depth_unit="bad"),
        modules={"plot_studio": {"enabled": True}},
    )

    saved = manager.save(config)
    loaded = manager.load("main project")
    backup = manager.backup("main project")

    assert saved.exists()
    assert backup.exists()
    assert loaded.settings.theme == "dark"
    assert loaded.settings.autosave_interval_minutes == 1
    assert loaded.settings.default_depth_unit == "m"
    assert loaded.modules["plot_studio"]["enabled"] is True
    assert "main_project" in manager.list_configurations()


def test_notification_center_filters_and_marks_read():
    center = NotificationCenter()
    first = center.push("LAS", "Импорт завершен", NotificationLevel.SUCCESS, source="las")
    center.push("Ошибка", "Нет файла", "error", source="report")

    assert len(center.list()) == 2
    assert len(center.list(level="error")) == 1
    assert center.mark_read(first.id) is True
    assert all(item.id != first.id for item in center.list(unread_only=True))


def test_task_manager_tracks_progress_and_status():
    manager = TaskManager()
    task = manager.create("Export report", "report_export")
    updated = manager.update(task.id, status=TaskStatus.RUNNING, progress=45, message="Rendering")
    completed = manager.update(task.id, status="completed", progress=120)

    assert updated.message == "Rendering"
    assert completed.progress == 100
    assert completed.status == TaskStatus.COMPLETED
    assert manager.list(status="completed") == [completed]


def test_logging_center_reads_filters_and_exports(tmp_path):
    center = LoggingCenter(tmp_path)
    center.append("Workspace started", "INFO", "workspace")
    center.append("LAS export failed", "ERROR", "las")

    errors = center.read(level="ERROR")
    exported = center.export(tmp_path / "logs.json", errors)

    assert len(errors) == 1
    assert errors[0].source == "las"
    assert exported.exists()
    assert "LAS export failed" in exported.read_text(encoding="utf-8")


def test_service_registry_and_default_services(tmp_path):
    registry = ServiceRegistry()
    registry.register("settings", WorkspaceSettings())
    captured = {}
    registry.bind_plugin_api(lambda name, service: captured.setdefault(name, service))

    assert registry.names() == ["settings"]
    assert "settings" in captured

    default_registry = build_default_workspace_services(tmp_path)
    assert {"configuration", "logs", "notifications", "settings", "tasks"}.issubset(set(default_registry.names()))
