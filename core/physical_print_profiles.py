"""Shared physical print profiles for engineering documents and plots.

Built-in profiles define the readability floor for each paper/orientation pair.
User profiles may tighten quality, margins and pagination, but they may never
relax the built-in safety floor.  This keeps custom A4/A3 output readable while
allowing repeatable organization-specific presets.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping


PAGE_SIZES_MM: dict[str, tuple[float, float]] = {
    "A4": (210.0, 297.0),
    "A3": (297.0, 420.0),
    "A2": (420.0, 594.0),
    "A1": (594.0, 841.0),
}
USER_PROFILE_PAGE_SIZES: tuple[str, ...] = ("A4", "A3")
USER_PROFILE_SCHEMA = "gas-ratio-pro.physical-print-profiles"
USER_PROFILE_VERSION = 1


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
    name: str = ""
    source: str = "builtin"

    @property
    def page_width_mm(self) -> float:
        width, height = PAGE_SIZES_MM[self.page_size]
        return height if self.orientation == "landscape" else width

    @property
    def page_height_mm(self) -> float:
        width, height = PAGE_SIZES_MM[self.page_size]
        return width if self.orientation == "landscape" else height

    @property
    def user_defined(self) -> bool:
        return self.source == "user"

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name or self.id,
            "source": self.source,
            "user_defined": self.user_defined,
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
    profile_id = f"{page_size.lower()}_{orientation}"
    return PhysicalPrintProfile(
        id=profile_id,
        name=f"{page_size} {orientation}",
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


def _float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _slug(value: object) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return normalized or "profile"


def build_user_physical_print_profile(
    *,
    profile_id: str = "",
    name: str,
    page_size: str,
    orientation: str,
    margin_mm: float = 12.0,
    dpi: int = 150,
    minimum_font_pt: float | None = None,
    minimum_line_width_pt: float | None = None,
    minimum_track_width_mm: float | None = None,
    max_tracks_per_page: int | None = None,
    legend_position: str = "bottom",
) -> PhysicalPrintProfile:
    """Create a safe user profile derived from an A4/A3 built-in baseline.

    Readability values are clamped to the baseline.  Track capacity may only be
    reduced, never increased beyond the baseline, because increasing capacity
    would implicitly shrink tracks below the certified minimum width.
    """

    normalized_size = str(page_size or "A4").strip().upper()
    if normalized_size not in USER_PROFILE_PAGE_SIZES:
        raise ValueError(f"unsupported_user_profile_page_size:{normalized_size}")
    normalized_orientation = str(orientation or "landscape").strip().lower()
    if normalized_orientation not in {"portrait", "landscape"}:
        raise ValueError(f"unsupported_user_profile_orientation:{normalized_orientation}")
    baseline = PHYSICAL_PRINT_PROFILES[f"{normalized_size.lower()}_{normalized_orientation}"]
    normalized_name = str(name or "").strip()
    if not normalized_name:
        raise ValueError("user_profile_name_required")
    normalized_id = str(profile_id or "").strip().lower()
    if not normalized_id:
        normalized_id = f"user_{_slug(normalized_name)}"
    if not normalized_id.startswith("user_"):
        normalized_id = f"user_{_slug(normalized_id)}"

    normalized_legend = str(legend_position or baseline.legend_position).strip().lower()
    if normalized_legend not in {"bottom", "right", "none"}:
        raise ValueError(f"unsupported_user_profile_legend_position:{normalized_legend}")

    safe_margin = min(35.0, max(5.0, _float(margin_mm, baseline.margin_mm)))
    safe_dpi = min(600, max(96, _int(dpi, 150)))
    safe_font = max(baseline.minimum_font_pt, _float(minimum_font_pt, baseline.minimum_font_pt))
    safe_line = max(
        baseline.minimum_line_width_pt,
        _float(minimum_line_width_pt, baseline.minimum_line_width_pt),
    )
    safe_track = max(
        baseline.minimum_track_width_mm,
        _float(minimum_track_width_mm, baseline.minimum_track_width_mm),
    )
    requested_tracks = _int(max_tracks_per_page, baseline.max_tracks_per_page)
    safe_tracks = max(1, min(baseline.max_tracks_per_page, requested_tracks))

    return PhysicalPrintProfile(
        id=normalized_id,
        name=normalized_name,
        source="user",
        page_size=normalized_size,
        orientation=normalized_orientation,
        margin_mm=round(safe_margin, 3),
        dpi=safe_dpi,
        minimum_font_pt=round(safe_font, 3),
        minimum_line_width_pt=round(safe_line, 3),
        minimum_track_width_mm=round(safe_track, 3),
        max_tracks_per_page=safe_tracks,
        legend_position=normalized_legend,
    )


def physical_print_profile_from_mapping(value: Mapping[str, Any]) -> PhysicalPrintProfile:
    """Deserialize and validate a user profile mapping."""

    return build_user_physical_print_profile(
        profile_id=str(value.get("id") or ""),
        name=str(value.get("name") or value.get("id") or ""),
        page_size=str(value.get("page_size") or "A4"),
        orientation=str(value.get("orientation") or "landscape"),
        margin_mm=_float(value.get("margin_mm"), 12.0),
        dpi=_int(value.get("dpi"), 150),
        minimum_font_pt=_float(value.get("minimum_font_pt"), 0.0),
        minimum_line_width_pt=_float(value.get("minimum_line_width_pt"), 0.0),
        minimum_track_width_mm=_float(value.get("minimum_track_width_mm"), 0.0),
        max_tracks_per_page=_int(value.get("max_tracks_per_page"), 1),
        legend_position=str(value.get("legend_position") or "bottom"),
    )


def resolve_physical_print_profile(
    page_size: str = "A4",
    orientation: str = "landscape",
    profile_id: str | None = None,
    *,
    custom_profile: Mapping[str, Any] | PhysicalPrintProfile | None = None,
) -> PhysicalPrintProfile:
    """Resolve a built-in profile or an explicitly supplied validated user profile."""

    if isinstance(custom_profile, PhysicalPrintProfile):
        profile = custom_profile
    elif isinstance(custom_profile, Mapping):
        profile = physical_print_profile_from_mapping(custom_profile)
    else:
        profile = None
    if profile is not None:
        requested = str(profile_id or profile.id).strip().lower()
        if requested and requested != profile.id:
            raise KeyError(requested)
        return profile

    key = str(profile_id or "").strip().lower()
    if not key:
        key = f"{str(page_size).strip().lower()}_{str(orientation).strip().lower()}"
    if key not in PHYSICAL_PRINT_PROFILES:
        raise KeyError(key)
    return PHYSICAL_PRINT_PROFILES[key]


class UserPhysicalPrintProfileStore:
    """Small JSON store for repeatable user A4/A3 print profiles."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else (
            Path(__file__).resolve().parents[1] / "data" / "user_preferences" / "physical_print_profiles.json"
        )

    def load(self) -> tuple[PhysicalPrintProfile, ...]:
        if not self.path.exists():
            return ()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return ()
        if not isinstance(payload, Mapping) or payload.get("schema") != USER_PROFILE_SCHEMA:
            return ()
        profiles: list[PhysicalPrintProfile] = []
        for item in payload.get("profiles", []):
            if not isinstance(item, Mapping):
                continue
            try:
                profiles.append(physical_print_profile_from_mapping(item))
            except (ValueError, KeyError, TypeError):
                continue
        deduplicated = {profile.id: profile for profile in profiles}
        return tuple(sorted(deduplicated.values(), key=lambda item: (item.name.lower(), item.id)))

    def save(self, profiles: Iterable[PhysicalPrintProfile]) -> Path:
        safe_profiles: dict[str, PhysicalPrintProfile] = {}
        for profile in profiles:
            if not isinstance(profile, PhysicalPrintProfile) or not profile.user_defined:
                continue
            safe_profiles[profile.id] = physical_print_profile_from_mapping(profile.to_dict())
        payload = {
            "schema": USER_PROFILE_SCHEMA,
            "version": USER_PROFILE_VERSION,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "profiles": [profile.to_dict() for profile in sorted(safe_profiles.values(), key=lambda item: item.id)],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)
        return self.path

    def upsert(self, profile: PhysicalPrintProfile) -> PhysicalPrintProfile:
        if not profile.user_defined:
            raise ValueError("only_user_profiles_can_be_persisted")
        safe = physical_print_profile_from_mapping(profile.to_dict())
        profiles = {item.id: item for item in self.load()}
        profiles[safe.id] = safe
        self.save(profiles.values())
        return safe

    def delete(self, profile_id: str) -> bool:
        normalized = str(profile_id or "").strip().lower()
        profiles = {item.id: item for item in self.load()}
        existed = normalized in profiles
        profiles.pop(normalized, None)
        self.save(profiles.values())
        return existed

    def resolve(self, profile_id: str) -> PhysicalPrintProfile:
        normalized = str(profile_id or "").strip().lower()
        for profile in self.load():
            if profile.id == normalized:
                return profile
        raise KeyError(normalized)


def available_physical_print_profiles(
    user_profiles: Iterable[PhysicalPrintProfile] = (),
    *,
    user_page_sizes_only: bool = False,
) -> tuple[PhysicalPrintProfile, ...]:
    builtins = tuple(
        profile
        for profile in PHYSICAL_PRINT_PROFILES.values()
        if not user_page_sizes_only or profile.page_size in USER_PROFILE_PAGE_SIZES
    )
    safe_users = tuple(profile for profile in user_profiles if profile.user_defined)
    return (*builtins, *safe_users)


__all__ = [
    "PAGE_SIZES_MM",
    "USER_PROFILE_PAGE_SIZES",
    "PHYSICAL_PRINT_PROFILES",
    "PhysicalPrintProfile",
    "UserPhysicalPrintProfileStore",
    "available_physical_print_profiles",
    "build_user_physical_print_profile",
    "physical_print_profile_from_mapping",
    "resolve_physical_print_profile",
]
