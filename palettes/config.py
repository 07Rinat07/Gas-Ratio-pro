from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PixlerZone:
    name: str
    y_min: float
    y_max: float
    color: str


@dataclass(frozen=True)
class TernaryRegion:
    name: str
    a: tuple[float, ...]
    b: tuple[float, ...]
    c: tuple[float, ...]
    color: str


@dataclass(frozen=True)
class PaletteConfig:
    version: str
    notice: str
    pixler_zones: tuple[PixlerZone, ...]
    ternary_regions: tuple[TernaryRegion, ...]


# Визуальные границы v0.3/v0.4 являются черновыми и должны быть заменены на
# точные корпоративные линии после подтверждения методики.
DEFAULT_PIXLER_ZONES: tuple[PixlerZone, ...] = (
    PixlerZone("Oil", 1.0, 20.0, "rgba(45, 140, 85, 0.16)"),
    PixlerZone("Gas", 20.0, 200.0, "rgba(30, 115, 190, 0.14)"),
    PixlerZone("Non-Productive", 200.0, 10000.0, "rgba(150, 150, 150, 0.13)"),
)

DEFAULT_TERNARY_REGIONS: tuple[TernaryRegion, ...] = ()

DEFAULT_PALETTE_CONFIG = PaletteConfig(
    version="built-in",
    notice=(
        "Встроенные визуальные границы являются черновыми и требуют "
        "подтверждения по корпоративной методике."
    ),
    pixler_zones=DEFAULT_PIXLER_ZONES,
    ternary_regions=DEFAULT_TERNARY_REGIONS,
)


def default_palette_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "palettes.json"


def _read_float(value: object, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid palette config value for {field_name}: {value!r}") from exc


def _read_float_sequence(value: object, field_name: str) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) < 3:
        raise ValueError(f"Palette field {field_name} must contain at least 3 numeric points.")
    return tuple(_read_float(item, field_name) for item in value)


def _load_pixler_zones(raw_zones: object) -> tuple[PixlerZone, ...]:
    if not isinstance(raw_zones, list) or not raw_zones:
        raise ValueError("Palette config must contain at least one Pixler zone.")

    zones: list[PixlerZone] = []
    for index, raw_zone in enumerate(raw_zones):
        if not isinstance(raw_zone, dict):
            raise ValueError(f"Pixler zone #{index + 1} must be an object.")

        name = str(raw_zone.get("name", "")).strip()
        color = str(raw_zone.get("color", "")).strip()
        y_min = _read_float(raw_zone.get("y_min"), f"pixler.zones[{index}].y_min")
        y_max = _read_float(raw_zone.get("y_max"), f"pixler.zones[{index}].y_max")

        if not name:
            raise ValueError(f"Pixler zone #{index + 1} has empty name.")
        if not color:
            raise ValueError(f"Pixler zone {name} has empty color.")
        if y_min <= 0 or y_max <= 0 or y_min >= y_max:
            raise ValueError(f"Pixler zone {name} must have 0 < y_min < y_max.")

        zones.append(PixlerZone(name=name, y_min=y_min, y_max=y_max, color=color))

    return tuple(zones)


def _load_ternary_regions(raw_regions: object) -> tuple[TernaryRegion, ...]:
    if raw_regions is None:
        return ()
    if not isinstance(raw_regions, list):
        raise ValueError("Palette config ternary.regions must be a list.")

    regions: list[TernaryRegion] = []
    for index, raw_region in enumerate(raw_regions):
        if not isinstance(raw_region, dict):
            raise ValueError(f"Ternary region #{index + 1} must be an object.")

        name = str(raw_region.get("name", "")).strip()
        color = str(raw_region.get("color", "")).strip()
        a = _read_float_sequence(raw_region.get("a"), f"ternary.regions[{index}].a")
        b = _read_float_sequence(raw_region.get("b"), f"ternary.regions[{index}].b")
        c = _read_float_sequence(raw_region.get("c"), f"ternary.regions[{index}].c")

        if not name:
            raise ValueError(f"Ternary region #{index + 1} has empty name.")
        if not color:
            raise ValueError(f"Ternary region {name} has empty color.")
        if not (len(a) == len(b) == len(c)):
            raise ValueError(f"Ternary region {name} must have equal a/b/c point counts.")

        regions.append(TernaryRegion(name=name, a=a, b=b, c=c, color=color))

    return tuple(regions)


def load_palette_config(path: str | Path | None = None) -> PaletteConfig:
    config_path = Path(path) if path is not None else default_palette_config_path()
    if not config_path.exists():
        return DEFAULT_PALETTE_CONFIG

    with config_path.open("r", encoding="utf-8") as file:
        raw_config = json.load(file)

    if not isinstance(raw_config, dict):
        raise ValueError("Palette config root must be an object.")

    pixler = raw_config.get("pixler", {})
    ternary = raw_config.get("ternary", {})
    if not isinstance(pixler, dict):
        raise ValueError("Palette config pixler section must be an object.")
    if not isinstance(ternary, dict):
        raise ValueError("Palette config ternary section must be an object.")

    return PaletteConfig(
        version=str(raw_config.get("version", "custom")),
        notice=str(raw_config.get("notice", DEFAULT_PALETTE_CONFIG.notice)),
        pixler_zones=_load_pixler_zones(pixler.get("zones")),
        ternary_regions=_load_ternary_regions(ternary.get("regions")),
    )