from pathlib import Path

from core.build_info import BUILD_VERSION, runtime_build_info


def test_runtime_build_identity_points_to_current_project() -> None:
    info = runtime_build_info()
    root = Path(info.project_root)
    assert BUILD_VERSION == "v201"
    assert info.version == "v201"
    assert info.channel == "workbench-live-interaction-completion"
    assert root.is_dir()
    assert Path(info.entry_point) == root / "app" / "streamlit_app.py"


def test_launcher_guards_stale_port_and_prints_source() -> None:
    script = Path("run_app.ps1").read_text(encoding="utf-8")
    assert "Get-NetTCPConnection" in script
    assert "-ForceRestart" in script
    assert "Source: $ProjectRoot" in script
    assert "$env:GAS_RATIO_PRO_LEGACY_UI = \"\"" in script
    assert "Starting Gas Ratio Pro v200" in script


def test_renderer_exposes_build_and_runtime_source() -> None:
    renderer = Path("app/workbench_renderer.py").read_text(encoding="utf-8")
    assert "Build <b>" in renderer
    assert "runtime_build_info" in renderer
    assert "runtime_build_info" in renderer
