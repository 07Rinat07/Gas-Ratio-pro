"""Shared physical print profiles for engineering documents and plots.

The profiles describe paper geometry and readability floors in physical units.
Renderers may use different drawing technologies, but they must resolve the
same profile so an A4/A3 export keeps identical margins, typography and track
pagination decisions.
"""

from __future__ import annotations

from dataclasses import dataclass


PAGE_SIZES_MM: dict[str, tuple[float, float]] = {
    "A4": (210.0, 297.0),
    "A3": (297.0, 420.0),
    "A2": (420.0, 594.0),
    "A1": (594.0, 841.0),
}


@dataclass(frozen=True, slots=True)
class PhysicalPrintProfile:
    """Immutable paper/readability contract shared by export renderers."""

    id: str
    page_size: str
    orientation: str
    margin_mm: float
    dpi: int
    minimum_font_pt: float
    minimum_line_width_pt: float
    minimum_track_width_mm: float
    max_tracks_per_page: int
    legend_position: str = "bottom"

    @property
    def page_width_mm(self) -> float:
        width, height = PAGE_SIZES_MM[self.page_size]
        return height if self.orientation == "landscape" else width

    @property
    def page_height_mm(self) -> float:
        width, height = PAGE_SIZES_MM[self.page_size]
        return width if self.orientation == "landscape" else height

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "page_size": self.page_size,
            "orientation": self.orientation,
            "page_width_mm": self.page_width_mm,
            "page_height_mm": self.page_height_mm,
            "margin_mm": self.margin_mm,
            "dpi": self.dpi,
            "minimum_font_pt": self.minimum_font_pt,
            "minimum_line_width_pt": self.minimum_line_width_pt,
            "minimum_track_width_mm": self.minimum_track_width_mm,
            "max_tracks_per_page": self.max_tracks_per_page,
            "legend_position": self.legend_position,
        }


def _profile(
    page_size: str,
    orientation: str,
    *,
    minimum_font_pt: float,
    minimum_line_width_pt: float,
    minimum_track_width_mm: float,
    max_tracks_per_page: int,
) -> PhysicalPrintProfile:
    return PhysicalPrintProfile(
        id=f"{page_size.lower()}_{orientation}",
        page_size=page_size,
        orientation=orientation,
        margin_mm=12.0,
        dpi=96,
        minimum_font_pt=minimum_font_pt,
        minimum_line_width_pt=minimum_line_width_pt,
        minimum_track_width_mm=minimum_track_width_mm,
        max_tracks_per_page=max_tracks_per_page,
    )


PHYSICAL_PRINT_PROFILES: dict[str, PhysicalPrintProfile] = {
    item.id: item
    for item in (
        _profile("A4", "portrait", minimum_font_pt=7.5, minimum_line_width_pt=0.50, minimum_track_width_mm=28.0, max_tracks_per_page=4),
        _profile("A4", "landscape", minimum_font_pt=7.5, minimum_line_width_pt=0.50, minimum_track_width_mm=28.0, max_tracks_per_page=6),
        _profile("A3", "portrait", minimum_font_pt=8.0, minimum_line_width_pt=0.55, minimum_track_width_mm=30.0, max_tracks_per_page=6),
        _profile("A3", "landscape", minimum_font_pt=8.0, minimum_line_width_pt=0.55, minimum_track_width_mm=30.0, max_tracks_per_page=9),
        _profile("A2", "portrait", minimum_font_pt=8.0, minimum_line_width_pt=0.60, minimum_track_width_mm=32.0, max_tracks_per_page=10),
        _profile("A2", "landscape", minimum_font_pt=8.0, minimum_line_width_pt=0.60, minimum_track_width_mm=32.0, max_tracks_per_page=14),
        _profile("A1", "portrait", minimum_font_pt=8.0, minimum_line_width_pt=0.60, minimum_track_width_mm=32.0, max_tracks_per_page=18),
        _profile("A1", "landscape", minimum_font_pt=8.0, minimum_line_width_pt=0.60, minimum_track_width_mm=32.0, max_tracks_per_page=24),
    )
}


def resolve_physical_print_profile(
    page_size: str = "A4",
    orientation: str = "landscape",
    profile_id: str | None = None,
) -> PhysicalPrintProfile:
    """Resolve a named profile or the canonical paper/orientation profile."""

    key = str(profile_id or "").strip().lower()
    if not key:
        key = f"{str(page_size).strip().lower()}_{str(orientation).strip().lower()}"
    if key not in PHYSICAL_PRINT_PROFILES:
        raise KeyError(key)
    return PHYSICAL_PRINT_PROFILES[key]

