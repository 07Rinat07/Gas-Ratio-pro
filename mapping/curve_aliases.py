from __future__ import annotations

import re
from functools import lru_cache


CURVE_ALIASES: dict[str, tuple[str, ...]] = {
    "well": (
        "well",
        "well name",
        "wellname",
        "well id",
        "well_id",
        "borehole",
        "скважина",
        "имя скважины",
    ),
    "depth": (
        "depth",
        "dept",
        "md",
        "measured depth",
        "measured_depth",
        "глубина",
    ),
    "depth_from": (
        "from",
        "top",
        "depth from",
        "depth_from",
        "interval from",
        "от",
    ),
    "depth_to": (
        "to",
        "base",
        "bottom",
        "depth to",
        "depth_to",
        "interval to",
        "до",
    ),
    "c1": (
        "c1",
        "ch4",
        "methane",
        "метан",
    ),
    "c2": (
        "c2",
        "ethane",
        "этан",
    ),
    "c3": (
        "c3",
        "propane",
        "пропан",
    ),
    "ic4": (
        "ic4",
        "i-c4",
        "i c4",
        "iso c4",
        "isobutane",
        "iso-butane",
        "изобутан",
    ),
    "nc4": (
        "nc4",
        "n-c4",
        "n c4",
        "normal c4",
        "normal butane",
        "n-butane",
        "н-бутан",
        "н бутан",
    ),
    "ic5": (
        "ic5",
        "i-c5",
        "i c5",
        "iso c5",
        "isopentane",
        "iso-pentane",
        "изопентан",
    ),
    "nc5": (
        "nc5",
        "n-c5",
        "n c5",
        "normal c5",
        "normal pentane",
        "n-pentane",
        "н-пентан",
        "н пентан",
    ),
    "co2": (
        "co2",
        "carbon dioxide",
        "углекислый газ",
    ),
    "h2s": (
        "h2s",
        "hydrogen sulfide",
        "сероводород",
    ),
    "rop": (
        "rop",
        "rate of penetration",
        "скорость проходки",
    ),
    "lithology": (
        "lithology",
        "lith",
        "литология",
    ),
}


def normalize_curve_name(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.strip().lower()
    text = text.replace("ё", "е")
    return re.sub(r"[^0-9a-zа-я]+", "", text)


@lru_cache(maxsize=1)
def alias_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for standard_name, aliases in CURVE_ALIASES.items():
        lookup[normalize_curve_name(standard_name)] = standard_name
        for alias in aliases:
            lookup[normalize_curve_name(alias)] = standard_name
    return lookup
