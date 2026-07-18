from pathlib import Path

from core.build_info import BUILD_VERSION, runtime_build_info


def test_runtime_build_identity_points_to_current_project() -> None:
    info = runtime_build_info()
    root = Path(info.project_root)
    assert info.version == BUILD_VERSION
    assert info.version.startswith("v225.")
    assert info.channel in {"stable", "release-candidate"}
    assert root.is_dir()
    assert Path(info.entry_point) == root / "app" / "streamlit_app.py"

def test_launcher_guards_stale_port_and_prints_source() -> None:
    from core.ui_behavior_contracts import LAUNCHER_BEHAVIOR

    info = runtime_build_info()
    assert LAUNCHER_BEHAVIOR.guards_stale_port is True
    assert LAUNCHER_BEHAVIOR.force_restart_supported is True
    assert LAUNCHER_BEHAVIOR.prints_project_source is True
    assert LAUNCHER_BEHAVIOR.clears_legacy_ui_flag is True
    assert Path(info.project_root).is_dir()
    assert Path(info.entry_point).exists()


def test_renderer_exposes_build_and_runtime_source() -> None:
    from app.workbench_renderer import workbench_build_badge

    badge = workbench_build_badge()
    info = runtime_build_info()
    assert badge["version"] == info.version
    assert badge["channel"] == info.channel
    assert Path(badge["project_root"]) == Path(info.project_root)
    assert Path(badge["entry_point"]) == Path(info.entry_point)
