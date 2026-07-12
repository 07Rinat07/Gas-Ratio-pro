from app.workbench_renderer import build_workbench_responsive_css
from core.build_info import BUILD_CHANNEL, BUILD_VERSION, runtime_build_info
from pathlib import Path


def test_v199_runtime_identity():
    assert BUILD_VERSION == "v221-rc2"
    assert BUILD_CHANNEL == "release-candidate"
    assert runtime_build_info().version == "v221-rc2"


def test_v199_css_has_professional_regions_and_readable_controls():
    css = build_workbench_responsive_css()
    for token in (
        "workbench-titlebar", "workbench-menu", "workbench-ribbon",
        "workbench-workspace-shell", "workbench-pane-title",
        "workbench-statusbar", "min-height: 44px",
    ):
        assert token in css
    assert "workbench-quick-actions" in css


def test_stage4_remains_open_until_live_ux_acceptance():
    roadmap = Path("docs/PROJECT_ROADMAP.md").read_text(encoding="utf-8")
    status = Path("docs/PROJECT_STATUS.md").read_text(encoding="utf-8")
    assert "IN PROGRESS v214" in roadmap
    assert "Live visual acceptance" in roadmap
    assert "Stage 5: **BLOCKED**" in status
    assert "BLOCKED" in status
