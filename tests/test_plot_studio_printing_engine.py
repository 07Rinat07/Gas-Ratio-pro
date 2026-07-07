from __future__ import annotations

import pytest

from projects import create_project
from projects.plot_studio import add_plot_curve, add_plot_track, save_plot_template
from projects.plot_studio_core import PlotViewportState, PlotWorkspace, build_plot_depth_range, build_plot_workspace
from projects.plot_studio_printing_engine import (
    PlotPrintConfig,
    build_plot_print_manifest,
    build_plot_print_manifest_dict,
    build_plot_print_page_table,
    create_plot_print_job,
    validate_plot_print_config,
)
from projects.plot_studio_track_layout import PlotTrackLayoutConfig


def _workspace(tmp_path):
    project = create_project(tmp_path, name="Print Engine")
    template = save_plot_template(tmp_path, project.id, "Print Tablet", template_id="print-tablet", well_id="well-01")
    template = add_plot_track(tmp_path, project.id, template.id, "Gamma", track_id="track-gamma", width=1.0)
    template = add_plot_track(tmp_path, project.id, template.id, "Density", track_id="track-density", width=2.0)
    template = add_plot_curve(tmp_path, project.id, template.id, "GR", "track-gamma", curve_id="curve-gr")
    template = add_plot_curve(tmp_path, project.id, template.id, "RHOB", "track-density", curve_id="curve-rhob")
    return build_plot_workspace(template, depth_from=1000, depth_to=1600)


def test_print_config_validates_page_settings():
    cfg = validate_plot_print_config(PlotPrintConfig(page_size="A4", orientation="LANDSCAPE", dpi="300"))  # type: ignore[arg-type]

    assert cfg.page_size == "a4"
    assert cfg.orientation == "landscape"
    assert cfg.dpi == 300

    with pytest.raises(ValueError, match="A4, A3"):
        validate_plot_print_config(PlotPrintConfig(page_size="legal"))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="portrait"):
        validate_plot_print_config(PlotPrintConfig(orientation="diagonal"))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="72..1200"):
        validate_plot_print_config(PlotPrintConfig(dpi=20))


def test_print_config_rejects_invalid_margins_and_scale():
    with pytest.raises(ValueError, match="левое и правое поля"):
        validate_plot_print_config(PlotPrintConfig(page_size="a4", margin_left_mm=120, margin_right_mm=120))

    with pytest.raises(ValueError, match="верхнее и нижнее поля"):
        validate_plot_print_config(PlotPrintConfig(page_size="a4", margin_top_mm=200, margin_bottom_mm=200))

    with pytest.raises(ValueError, match="fixed scale"):
        validate_plot_print_config(PlotPrintConfig(fixed_scale=0))


def test_print_manifest_builds_page_geometry_and_layout(tmp_path):
    workspace = _workspace(tmp_path)

    manifest = build_plot_print_manifest(
        workspace,
        layout_config=PlotTrackLayoutConfig(canvas_width_px=1200),
        print_config=PlotPrintConfig(page_size="a3", orientation="portrait", dpi=300),
    )

    assert manifest.workspace_id == "print-tablet"
    assert manifest.page_size == "a3"
    assert manifest.page_width_px > 0
    assert manifest.printable_width_px < manifest.page_width_px
    assert manifest.layout["workspace_id"] == "print-tablet"
    assert manifest.page_count >= 1
    assert manifest.pages[0].depth_from == 1000
    assert manifest.pages[-1].depth_to == 1600


def test_print_manifest_supports_fixed_scale_and_page_splitting(tmp_path):
    workspace = _workspace(tmp_path)

    manifest = build_plot_print_manifest(
        workspace,
        print_config=PlotPrintConfig(page_size="a4", dpi=96, scale_mode="fixed_scale", fixed_scale=8.0),
    )

    assert manifest.scale_mode == "fixed_scale"
    assert manifest.scale == 8.0
    assert manifest.page_count > 1
    assert any("разбит" in message for message in manifest.messages)


def test_print_job_reports_not_ready_without_tracks():
    workspace = PlotWorkspace(
        template_id="empty-print",
        name="Empty Print",
        well_id="",
        viewport=PlotViewportState(depth_range=build_plot_depth_range(0, 100)),
        tracks=(),
    )

    job = create_plot_print_job(workspace)

    assert job.ready is False
    assert any("нет видимых треков" in message for message in job.messages)


def test_print_manifest_dict_and_page_table_are_ui_ready(tmp_path):
    workspace = _workspace(tmp_path)
    manifest = build_plot_print_manifest(workspace, print_config=PlotPrintConfig(include_legend=False))

    payload = build_plot_print_manifest_dict(manifest)
    table = build_plot_print_page_table(manifest)

    assert payload["options"]["include_legend"] is False
    assert payload["pages"][0]["page_number"] == 1
    assert table[0]["Страница"] == 1
    assert "Масштаб" in table[0]
