from __future__ import annotations

from services.visualization_print_layout import VisualizationPrintLayoutEngine


def _layout():
    return {"width": 900, "height": 1200}


def _legend():
    return {"legend_items": [{"id": "legend.GR"}, {"id": "legend.gas"}]}


def test_print_layout_builds_a4_landscape_page_with_legend_region():
    result = VisualizationPrintLayoutEngine().build(_layout(), _legend()).to_dict()

    assert result["schema"] == "visualization.print.layout"
    assert result["ok"] is True
    assert result["page_size"] == "A4"
    assert result["orientation"] == "landscape"
    assert result["metadata"]["page_count"] == 1
    assert result["metadata"]["legend_reserved"] is True
    assert result["pages"][0]["legend_bounds"] is not None
    assert 0 < result["pages"][0]["content_scale"] <= 1
    assert result["renderer_neutral"] is True


def test_print_layout_supports_portrait_right_legend_and_fit_width():
    result = VisualizationPrintLayoutEngine().build(
        _layout(),
        _legend(),
        {
            "page_size": "A3",
            "orientation": "portrait",
            "scale_mode": "fit_width",
            "legend_position": "right",
            "margin_mm": 15,
            "dpi": 144,
        },
    ).to_dict()

    assert result["ok"] is True
    assert result["page_size"] == "A3"
    assert result["orientation"] == "portrait"
    assert result["dpi"] == 144
    assert result["pages"][0]["legend_bounds"]["height"] == result["pages"][0]["printable_bounds"]["height"]


def test_print_layout_reports_invalid_options_without_crashing():
    result = VisualizationPrintLayoutEngine().build(
        {"width": 0, "height": 0},
        {},
        {"page_size": "LEGAL", "orientation": "diagonal", "scale_mode": "stretch"},
    ).to_dict()

    assert result["ok"] is False
    assert "print_layout_error:unsupported_page_size:LEGAL" in result["issues"]
    assert "print_layout_error:unsupported_orientation:diagonal" in result["issues"]
    assert "print_layout_error:unsupported_scale_mode:stretch" in result["issues"]
    assert "print_layout_error:invalid_source_bounds" in result["issues"]
