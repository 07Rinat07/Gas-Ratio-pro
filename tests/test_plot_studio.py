from __future__ import annotations

from pathlib import Path

import pytest

from projects import create_project
from projects.plot_studio import (
    PlotAxisConfig,
    add_plot_annotation,
    add_plot_curve,
    add_plot_track,
    build_plot_studio_curve_table,
    build_plot_studio_template_table,
    build_plot_studio_track_table,
    get_plot_template,
    list_plot_templates,
    save_plot_template,
    summarize_plot_studio,
)


def test_plot_studio_creates_template_tracks_curves_and_annotations(tmp_path: Path):
    project = create_project(tmp_path, name="Plot Studio Demo")

    template = save_plot_template(tmp_path, project.id, "Triple Combo", template_id="triple-combo", well_id="well-01")
    template = add_plot_track(tmp_path, project.id, template.id, "Density Neutron", track_id="track-density", width=1.2)
    template = add_plot_curve(tmp_path, project.id, template.id, "RHOB", "track-density", color="#22c55e", line_style="dash", axis=PlotAxisConfig(scale="linear", min_value=1.95, max_value=2.95))
    template = add_plot_annotation(tmp_path, project.id, template.id, "A10 top", 1510.0, track_id="track-density", annotation_type="top")

    summary = summarize_plot_studio(tmp_path, project.id)
    loaded = get_plot_template(tmp_path, project.id, "triple-combo")

    assert loaded.name == "Triple Combo"
    assert len(loaded.tracks) == 4
    assert loaded.curves[0].mnemonic == "RHOB"
    assert loaded.annotations[0].text == "A10 top"
    assert summary.templates == 1
    assert summary.tracks == 4
    assert summary.curves == 1
    assert summary.annotations == 1


def test_plot_studio_tables_and_listing(tmp_path: Path):
    project = create_project(tmp_path, name="Plot Studio Tables")
    template = save_plot_template(
        tmp_path,
        project.id,
        "Quick Log",
        template_id="quick-log",
        tracks=[{"id": "track-gr", "title": "Gamma Ray", "width": 1.0}],
        curves=[{"id": "curve-gr", "mnemonic": "GR", "track_id": "track-gr"}],
    )

    templates = list_plot_templates(tmp_path, project.id)
    template_table = build_plot_studio_template_table(templates)
    track_table = build_plot_studio_track_table(template)
    curve_table = build_plot_studio_curve_table(template)

    assert template_table[0]["Шаблон"] == "Quick Log"
    assert track_table[0]["Трек"] == "Gamma Ray"
    assert track_table[0]["Кривые"] == 1
    assert curve_table[0]["Кривая"] == "GR"


def test_plot_studio_validates_axis_tracks_and_exports(tmp_path: Path):
    project = create_project(tmp_path, name="Plot Studio Validation")
    template = save_plot_template(tmp_path, project.id, "Validation", template_id="validation")

    with pytest.raises(ValueError, match="Трек missing-track не найден"):
        add_plot_curve(tmp_path, project.id, template.id, "GR", "missing-track")

    with pytest.raises(ValueError, match="Диапазон оси"):
        add_plot_curve(tmp_path, project.id, template.id, "GR", "track-gamma", axis={"min_value": 100, "max_value": 10})

    with pytest.raises(ValueError, match="Формат экспорта"):
        save_plot_template(tmp_path, project.id, "Bad Export", export_formats=["exe"])


def test_plot_studio_track_curve_editing_and_export_manifest(tmp_path: Path):
    project = create_project(tmp_path, name="Plot Studio Editing")
    template = save_plot_template(tmp_path, project.id, "Editing", template_id="editing")
    template = add_plot_track(tmp_path, project.id, template.id, "Sonic", track_id="track-sonic", width=0.9)
    template = add_plot_curve(tmp_path, project.id, template.id, "DT", "track-sonic", curve_id="curve-dt")

    from projects.plot_studio import (
        build_plot_export_manifest,
        remove_plot_curve,
        remove_plot_track,
        reorder_plot_track,
        update_plot_curve,
        update_plot_track,
    )

    template = update_plot_track(tmp_path, project.id, template.id, "track-sonic", title="Acoustic", width=1.4, visible=False)
    assert template.tracks[-1].title == "Acoustic"
    assert template.tracks[-1].width == 1.4
    assert template.tracks[-1].visible is False

    template = update_plot_curve(
        tmp_path,
        project.id,
        template.id,
        "curve-dt",
        mnemonic="DTC",
        track_id="track-gamma",
        line_width=2.0,
        line_style="dot",
        axis={"scale": "log", "min_value": 1, "max_value": 1000},
    )
    moved_curve = next(curve for curve in template.curves if curve.id == "curve-dt")
    assert moved_curve.mnemonic == "DTC"
    assert moved_curve.track_id == "track-gamma"
    assert moved_curve.axis.scale == "log"
    assert "curve-dt" in next(track.curve_ids for track in template.tracks if track.id == "track-gamma")

    template = reorder_plot_track(tmp_path, project.id, template.id, "track-sonic", "left")
    assert [track.id for track in template.tracks][-2] == "track-sonic"

    manifest = build_plot_export_manifest(template)
    assert manifest["template_id"] == "editing"
    assert "pdf" in manifest["export_formats"]
    assert all(track["visible"] for track in manifest["tracks"])

    template = remove_plot_curve(tmp_path, project.id, template.id, "curve-dt")
    assert template.curves == ()
    assert all("curve-dt" not in track.curve_ids for track in template.tracks)

    template = remove_plot_track(tmp_path, project.id, template.id, "track-sonic")
    assert "track-sonic" not in {track.id for track in template.tracks}


def test_plot_studio_prevents_invalid_deletions_and_moves(tmp_path: Path):
    project = create_project(tmp_path, name="Plot Studio Guards")
    template = save_plot_template(
        tmp_path,
        project.id,
        "Single",
        template_id="single",
        tracks=[{"id": "track-only", "title": "Only", "width": 1.0}],
    )

    from projects.plot_studio import remove_plot_curve, remove_plot_track, reorder_plot_track, update_plot_curve

    with pytest.raises(ValueError, match="хотя бы один трек"):
        remove_plot_track(tmp_path, project.id, template.id, "track-only")

    with pytest.raises(ValueError, match="Направление"):
        reorder_plot_track(tmp_path, project.id, template.id, "track-only", "sideways")

    with pytest.raises(ValueError, match="Кривая missing не найдена"):
        remove_plot_curve(tmp_path, project.id, template.id, "missing")

    template = add_plot_curve(tmp_path, project.id, template.id, "GR", "track-only", curve_id="curve-gr")
    with pytest.raises(ValueError, match="Трек missing-track не найден"):
        update_plot_curve(tmp_path, project.id, template.id, "curve-gr", track_id="missing-track")
