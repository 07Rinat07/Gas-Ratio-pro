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
