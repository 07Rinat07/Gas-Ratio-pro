from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PixlerZone:
    name: str
    y_min: float
    y_max: float
    color: str


# Визуальные границы v0.3 вынесены в конфиг и должны быть заменены на
# точные корпоративные линии после подтверждения методики.
DEFAULT_PIXLER_ZONES: tuple[PixlerZone, ...] = (
    PixlerZone("Oil", 1.0, 20.0, "rgba(45, 140, 85, 0.16)"),
    PixlerZone("Gas", 20.0, 200.0, "rgba(30, 115, 190, 0.14)"),
    PixlerZone("Non-Productive", 200.0, 10000.0, "rgba(150, 150, 150, 0.13)"),
)
