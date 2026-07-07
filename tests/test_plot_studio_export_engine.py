from __future__ import annotations

import json
from pathlib import Path

import pytest

from projects import create_project
from projects.plot_studio import add_plot_curve, add_plot_track, save_plot_template
from projects.plot_studio_core import build_plot_workspace
from projects.plot_studio_export_engine import (
    PlotExportConfig,
    build_plot_export_manifest,
    build_plot_export_result_manifest,
    export_plot_studio,
    validate_plot_export_config,
)
from projects.plot_studio_track_layout import PlotTrackLayoutConfig


def _workspace(tmp_path: Path):
    project = create_project(tmp_path, name="Export Engine")
    template = save_plot_template(tmp_path, project.id, "Export Tablet", template_id="export-tablet", well_id="well-01")
    template = add_plot_track(tmp_path, project.id, template.id, "Gamma", track_id="track-gamma", width=1.0)
    template = add_plot_track(tmp_path, project.id, template.id, "Density", track_id="track-density", width=2.0)
    template = add_plot_curve(tmp_path, project.id, template.id, "GR", "track-gamma", curve_id="curve-gr")
    template = add_plot_curve(tmp_path, project.id, template.id, "RHOB", "track-density", curve_id="curve-rhob")
    return build_plot_workspace(template, depth_from=1000, depth_to=1600)


def test_export_config_validates_formats_and_print_settings():
    cfg = validate_plot_export_config(PlotExportConfig(formats=("PDF", "png", "pdf"), dpi="300", scale="1,5"))  # type: ignore[arg-type]

    assert cfg.formats == ("pdf", "png")
    assert cfg.dpi == 300
    assert cfg.scale == 1.5

    with pytest.raises(ValueError, match="PDF, PNG, SVG и TIFF"):
        validate_plot_export_config(PlotExportConfig(formats=("docx",)))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="72..1200"):
        validate_plot_export_config(PlotExportConfig(dpi=20))

    with pytest.raises(ValueError, match="0.1..8.0"):
        validate_plot_export_config(PlotExportConfig(scale=10.0))


def test_export_manifest_is_renderer_ready(tmp_path):
    workspace = _workspace(tmp_path)

    manifest = build_plot_export_manifest(
        workspace,
        layout_config=PlotTrackLayoutConfig(canvas_width_px=1400),
        export_config=PlotExportConfig(formats=("pdf", "svg"), dpi=300),
    )

    assert manifest.workspace_id == "export-tablet"
    assert manifest.formats == ("pdf", "svg")
    assert manifest.width_px > 0
    assert manifest.height_px > 0
    assert manifest.layout["canvas_width_px"] >= 1400
    assert manifest.artifacts == ()


def test_export_writes_all_requested_artifacts_and_manifest(tmp_path):
    workspace = _workspace(tmp_path)
    output_dir = tmp_path / "exports"

    result = export_plot_studio(
        workspace,
        output_dir,
        export_config=PlotExportConfig(formats=("pdf", "png", "svg", "tiff"), dpi=96, overwrite=True),
    )

    assert result.success is True
    assert {artifact.format for artifact in result.artifacts} == {"pdf", "png", "svg", "tiff"}
    for artifact in result.artifacts:
        path = Path(artifact.path)
        assert path.exists()
        assert path.stat().st_size == artifact.bytes_written
        assert artifact.width_px == result.manifest.width_px
    manifest_path = output_dir / "export_tablet.export_manifest.json"
    assert manifest_path.exists()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["workspace_id"] == "export-tablet"
    assert len(payload["artifacts"]) == 4


def test_export_refuses_overwrite_by_default(tmp_path):
    workspace = _workspace(tmp_path)
    output_dir = tmp_path / "exports"
    export_plot_studio(workspace, output_dir, export_config=PlotExportConfig(formats=("svg",)))

    with pytest.raises(FileExistsError):
        export_plot_studio(workspace, output_dir, export_config=PlotExportConfig(formats=("svg",)))


def test_export_result_manifest_serializes_artifacts(tmp_path):
    workspace = _workspace(tmp_path)
    result = export_plot_studio(workspace, tmp_path / "exports", export_config=PlotExportConfig(formats=("svg",)))

    payload = build_plot_export_result_manifest(result.manifest)

    assert payload["formats"] == ["svg"]
    assert payload["artifacts"][0]["format"] == "svg"
    assert payload["layout"]["workspace_id"] == "export-tablet"
