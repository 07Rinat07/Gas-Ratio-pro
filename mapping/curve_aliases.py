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


CYRILLIC_LOOKALIKE_TRANSLATION = str.maketrans(
    {
        "а": "a",
        "в": "b",
        "е": "e",
        "к": "k",
        "м": "m",
        "н": "n",
        "о": "o",
        "р": "p",
        "с": "c",
        "т": "t",
        "х": "x",
        "у": "y",
    }
)

UNIT_SUFFIXES = (
    "percent",
    "процент",
    "ppm",
    "ppmv",
    "pct",
    "vol",
    "объем",
    "газ",
    "gas",
    "мгм3",
    "mgm3",
    "м3",
)

GAS_COMPONENT_KEYS = ("ic4", "nc4", "ic5", "nc5", "ch4", "c1", "c2", "c3", "co2", "h2s")
GAS_COMPONENT_MAP = {"ch4": "c1", "co2": "co2", "h2s": "h2s"}


def normalize_curve_name(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.strip().lower().replace("ё", "е")
    text = re.sub(r"с\s*н\s*4", "ch4", text)
    text = text.translate(CYRILLIC_LOOKALIKE_TRANSLATION)
    return re.sub(r"[^0-9a-zа-я]+", "", text)


def _strip_unit_suffixes(value: str) -> str:
    result = value
    changed = True
    while changed:
        changed = False
        for suffix in UNIT_SUFFIXES:
            if result.endswith(suffix) and len(result) > len(suffix):
                result = result[: -len(suffix)]
                changed = True
    return result


def normalized_curve_candidates(value: object) -> tuple[str, ...]:
    normalized = normalize_curve_name(value)
    if not normalized:
        return ()

    candidates = [normalized]
    stripped = _strip_unit_suffixes(normalized)
    if stripped and stripped != normalized:
        candidates.append(stripped)

    for key in GAS_COMPONENT_KEYS:
        if normalized == key or normalized.startswith(key) or normalized.endswith(key):
            candidates.append(GAS_COMPONENT_MAP.get(key, key))

    return tuple(dict.fromkeys(candidates))


@lru_cache(maxsize=1)
def alias_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for standard_name, aliases in CURVE_ALIASES.items():
        lookup[normalize_curve_name(standard_name)] = standard_name
        for alias in aliases:
            lookup[normalize_curve_name(alias)] = standard_name
    return lookup
