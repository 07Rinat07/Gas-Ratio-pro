"""Application service for report-bound page-aware visualization previews.

The service is the only bridge from an in-memory report dataframe to the
Visualization Engine physical package. Document renderers receive the prepared
preview contract and never rebuild tracks, pagination, or page chrome.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.physical_print_profiles import PhysicalPrintProfile, physical_print_profile_from_mapping

import pandas as pd

from services.las_visualization_payload_service import (
    DEFAULT_CURVE_LIMIT,
    DEFAULT_SAMPLE_LIMIT,
    LasVisualizationPayload,
    LasVisualizationPayloadService,
)
from services.visualization_print_center_contract import (
    VisualizationPrintCenterPreparedPackage,
    VisualizationPrintCenterService,
)


@dataclass(frozen=True, slots=True)
class ReportPageAwarePreviewResult:
    visualization: LasVisualizationPayload
    prepared: VisualizationPrintCenterPreparedPackage
    report_payload: Mapping[str, Any]

    @property
    def export_ready(self) -> bool:
        return self.prepared.export_ready and bool(self.report_payload.get("preview"))

    def to_dict(self, *, include_payloads: bool = False) -> dict[str, Any]:
        preview = dict(self.report_payload.get("preview", {}) or {})
        if not include_payloads:
            preview.pop("svg", None)
            preview.pop("page_svgs", None)
            pages = preview.get("pages")
            if isinstance(pages, list):
                preview["pages"] = [
                    {key: value for key, value in dict(page).items() if key != "svg"}
                    for page in pages
                    if isinstance(page, Mapping)
                ]
        return {
            "schema": "gas-ratio-pro/report/page-aware-preview-result/v1",
            "version": "1.0",
            "preview": preview,
            "summary": self.prepared.summary.to_dict(),
            "geometry_signature": self.prepared.package.geometry_signature,
            "export_ready": self.export_ready,
            "single_page_fallback": False,
            "contains_raw_dataframe": False,
        }


class ReportPageAwarePreviewService:
    """Build one physical package for Print Center and all report renderers."""

    def __init__(
        self,
        payload_service: LasVisualizationPayloadService | None = None,
        print_center: VisualizationPrintCenterService | None = None,
    ) -> None:
        self._payload_service = payload_service or LasVisualizationPayloadService()
        self._print_center = print_center or VisualizationPrintCenterService()

    def prepare(
        self,
        frame: pd.DataFrame,
        *,
        project_id: str,
        source_id: str,
        title: str,
        locale: str = "ru",
        page_size: str = "A4",
        orientation: str = "landscape",
        margin_mm: float = 12.0,
        show_page_chrome: bool = True,
        footer_text: str = "GAS RATIO PRO",
        classification: str = "ENGINEERING USE",
        curve_limit: int = DEFAULT_CURVE_LIMIT,
        sample_limit: int = DEFAULT_SAMPLE_LIMIT,
        interval_ids: Sequence[str] | None = None,
        interval_metadata: Mapping[str, Mapping[str, Any]] | None = None,
        raster_dpi: int = 150,
        physical_profile: Mapping[str, Any] | PhysicalPrintProfile | None = None,
    ) -> ReportPageAwarePreviewResult:
        normalized_page_size = str(page_size or "A4").strip().upper()
        if normalized_page_size not in {"A4", "A3"}:
            normalized_page_size = "A4"
        normalized_orientation = str(orientation or "landscape").strip().lower()
        if normalized_orientation not in {"portrait", "landscape"}:
            normalized_orientation = "landscape"
        normalized_locale = str(locale or "ru").strip().lower()
        if normalized_locale not in {"ru", "kk", "en"}:
            normalized_locale = "ru"

        resolved_profile: PhysicalPrintProfile | None = None
        if isinstance(physical_profile, PhysicalPrintProfile):
            resolved_profile = physical_profile
        elif isinstance(physical_profile, Mapping):
            resolved_profile = physical_print_profile_from_mapping(physical_profile)
        if resolved_profile is not None:
            normalized_page_size = resolved_profile.page_size
            normalized_orientation = resolved_profile.orientation

        print_options = {
            "page_size": normalized_page_size,
            "orientation": normalized_orientation,
            "margin_mm": resolved_profile.margin_mm if resolved_profile is not None else max(0.0, float(margin_mm)),
            "dpi": resolved_profile.dpi if resolved_profile is not None else 96,
            "page_chrome": {
                "enabled": bool(show_page_chrome),
                "locale": normalized_locale,
                "title": str(title or "LAS visualization"),
                "classification": str(classification or ""),
                "footer_text": str(footer_text or "GAS RATIO PRO"),
                "repeat_legend": True,
            },
        }
        if resolved_profile is not None:
            print_options["profile_id"] = resolved_profile.id
            print_options["physical_profile"] = resolved_profile.to_dict()

        visualization = self._payload_service.build_from_frame(
            frame,
            project_id=project_id,
            las_id=source_id,
            curve_limit=curve_limit,
            sample_limit=sample_limit,
            interval_ids=interval_ids,
            interval_metadata=interval_metadata,
            print_options=print_options,
        )
        prepared = self._print_center.prepare(
            visualization.scene_pipeline,
            locale=normalized_locale,
            title=title,
            raster_dpi=raster_dpi,
        )
        report_payload = {
            "schema": "gas-ratio-pro/report/visualization-payload/v1",
            "preview": prepared.output_contract(title=title)["docx_html_preview"],
            "print_center_summary": prepared.summary.to_dict(),
            "geometry_signature": prepared.package.geometry_signature,
            "export_ready": prepared.export_ready,
            "contains_raw_dataframe": False,
        }
        return ReportPageAwarePreviewResult(
            visualization=visualization,
            prepared=prepared,
            report_payload=report_payload,
        )


__all__ = ["ReportPageAwarePreviewResult", "ReportPageAwarePreviewService"]
