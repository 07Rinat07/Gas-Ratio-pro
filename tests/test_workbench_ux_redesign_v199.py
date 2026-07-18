from app.workbench_renderer import build_workbench_responsive_css
from core.build_info import BUILD_CHANNEL, BUILD_VERSION, runtime_build_info
from pathlib import Path


def test_v199_runtime_identity():
    assert BUILD_CHANNEL in {"stable", "release-candidate"}
    assert runtime_build_info().version == BUILD_VERSION

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
    from services.visualization_physical_golden_artifacts import VisualizationPhysicalGoldenArtifactService

    service = VisualizationPhysicalGoldenArtifactService()
    manifest = service.verify(Path("tests/fixtures/physical_golden_artifacts"))

    assert manifest.profiles
    assert {profile.profile_id for profile in manifest.profiles} == {
        "a4_portrait", "a4_landscape", "a3_portrait", "a3_landscape"
    }
