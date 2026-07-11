from __future__ import annotations

from copy import deepcopy

from services.las_viewer_export import LasViewerExportService
from services.las_viewer_multitrack_builder import LasViewerMultiTrackBuilder
from services.las_viewer_navigation import LasViewerNavigationController
from services.las_viewer_shared_interaction import LasViewerSharedInteractionResult


def _payload(point_count: int = 201) -> dict:
    points = [[1000.0 + index, float(index % 80)] for index in range(point_count)]
    return {
        "project_id": "project-export",
        "las_id": "viewer-export.las",
        "depth_curve": "DEPT",
        "depth_unit": "M",
        "depth_range": {"start": 1000.0, "stop": points[-1][0]},
        "tracks": [
            {"id": "track.gamma", "title": "Гамма", "width": 1.0},
            {"id": "track.gas", "title": "Газ", "width": 1.0},
        ],
        "curves": [
            {"mnemonic": "GR", "track_id": "track.gamma", "unit": "API", "points": points},
            {"mnemonic": "TG", "track_id": "track.gas", "unit": "%", "points": points},
        ],
    }


def _controller() -> LasViewerNavigationController:
    prepared = LasViewerMultiTrackBuilder().build(_payload()).payload
    return LasViewerNavigationController(prepared)


def test_current_view_exports_svg_and_pdf_with_geometry_parity() -> None:
    controller = _controller()
    controller.fit(1040.0, 1080.0)

    bundle = LasViewerExportService().export_current_view(controller)

    assert bundle.ok is True
    assert bundle.svg.content.startswith(b"<svg")
    assert bundle.pdf.content.startswith(b"%PDF-")
    assert bundle.geometry_signature_match is True
    assert bundle.svg.viewport_start == 1040.0
    assert bundle.svg.viewport_stop == 1080.0
    assert bundle.svg.geometry_signature == bundle.pdf.geometry_signature
    assert bundle.qa["ok"] is True


def test_export_contract_is_compact_and_renderer_neutral() -> None:
    contract = LasViewerExportService().export_current_view(_controller()).to_dict()

    assert contract["schema"] == "las.viewer.export.bundle"
    assert contract["renderer_neutral"] is True
    assert contract["raw_dataframe_included"] is False
    assert contract["svg"]["raw_dataframe_included"] is False
    assert contract["pdf"]["raw_dataframe_included"] is False
    assert contract["svg"]["raw_dataframe_included"] is False


def test_export_uses_existing_current_pipeline_without_ui_layout_rebuild() -> None:
    controller = _controller()
    snapshot = controller.fit(1020.0, 1030.0).interaction
    original_signature_source = deepcopy(snapshot.render_result["viewport_result"]["pipeline"])

    bundle = LasViewerExportService().export_current_view(snapshot)

    assert bundle.ok is True
    assert snapshot.render_result["viewport_result"]["pipeline"] == original_signature_source
    assert bundle.svg.viewport_start == 1020.0
    assert bundle.svg.viewport_stop == 1030.0


def test_validation_blocks_invalid_current_view_export() -> None:
    snapshot = _controller().render().interaction
    broken = deepcopy(snapshot.render_result)
    pipeline = broken["viewport_result"]["pipeline"]
    pipeline["print_layout"]["pages"][0]["content_bounds"]["x"] = 0
    invalid_snapshot = LasViewerSharedInteractionResult(
        viewer_state=snapshot.viewer_state,
        render_result=broken,
        overlay=snapshot.overlay,
        render_model=snapshot.render_model,
    )

    bundle = LasViewerExportService().export_current_view(invalid_snapshot)

    assert bundle.ok is False
    assert bundle.svg.export_ready is False
    assert bundle.pdf.export_ready is False
    assert bundle.svg.content == b""
    assert bundle.pdf.content == b""
    assert bundle.svg.validation["export_allowed"] is False
    assert "svg_renderer_blocked_by_render_validation" in bundle.svg.issues
    assert "pdf_renderer_blocked_by_render_validation" in bundle.pdf.issues
