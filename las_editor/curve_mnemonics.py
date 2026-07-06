from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from las_correlation.core import CURVE_GROUP_LABELS
from las_editor.curve_categories import curve_category_label, suggest_curve_category
from las_editor.curve_grouping import curve_group_label, suggest_curve_group
from las_editor.curve_rename import normalize_curve_name
from las_editor.curve_units import curve_unit_label, suggest_curve_unit

MNEMONIC_DICTIONARY: dict[str, dict[str, str]] = {
    "DEPT": {"canonical": "DEPT", "label": "Measured depth", "group": "depth", "category": "depth_reference", "unit": "m", "aliases": "DEPTH, MD, DEP"},
    "DEPTH": {"canonical": "DEPT", "label": "Measured depth", "group": "depth", "category": "depth_reference", "unit": "m", "aliases": "DEPT, MD, DEP"},
    "MD": {"canonical": "DEPT", "label": "Measured depth", "group": "depth", "category": "depth_reference", "unit": "m", "aliases": "DEPT, DEPTH, DEP"},
    "GR": {"canonical": "GR", "label": "Gamma ray", "group": "gamma", "category": "petrophysics", "unit": "api", "aliases": "GAMMA, GRC"},
    "RT": {"canonical": "RT", "label": "True resistivity", "group": "resistivity", "category": "petrophysics", "unit": "ohmm", "aliases": "RDEEP, RESD, LLD"},
    "RHOB": {"canonical": "RHOB", "label": "Bulk density", "group": "density_neutron", "category": "petrophysics", "unit": "g_cm3", "aliases": "DEN, RHOZ"},
    "NPHI": {"canonical": "NPHI", "label": "Neutron porosity", "group": "density_neutron", "category": "petrophysics", "unit": "v_v", "aliases": "NPOR, TNPH"},
    "DT": {"canonical": "DT", "label": "Sonic transit time", "group": "petrophysics", "category": "petrophysics", "unit": "unitless", "aliases": "DTC, AC"},
    "TGAS": {"canonical": "TGAS", "label": "Total gas", "group": "total_gas", "category": "mud_gas", "unit": "percent", "aliases": "TG, TOTAL_GAS, GAS"},
    "C1": {"canonical": "C1", "label": "Methane", "group": "gas_component", "category": "mud_gas", "unit": "percent", "aliases": "CH4, METHANE"},
    "C2": {"canonical": "C2", "label": "Ethane", "group": "gas_component", "category": "mud_gas", "unit": "percent", "aliases": "ETHANE"},
    "C3": {"canonical": "C3", "label": "Propane", "group": "gas_component", "category": "mud_gas", "unit": "percent", "aliases": "PROPANE"},
    "IC4": {"canonical": "IC4", "label": "Iso-butane", "group": "gas_component", "category": "mud_gas", "unit": "percent", "aliases": "I-C4, IC4H10"},
    "NC4": {"canonical": "NC4", "label": "Normal butane", "group": "gas_component", "category": "mud_gas", "unit": "percent", "aliases": "N-C4, NC4H10"},
    "ROP": {"canonical": "ROP", "label": "Rate of penetration", "group": "drilling", "category": "drilling", "unit": "m_h", "aliases": "ROP_AVG"},
    "WOB": {"canonical": "WOB", "label": "Weight on bit", "group": "drilling", "category": "drilling", "unit": "unitless", "aliases": "BIT_WEIGHT"},
}

_ALIAS_LOOKUP: dict[str, str] = {}
for key, item in MNEMONIC_DICTIONARY.items():
    _ALIAS_LOOKUP[normalize_curve_name(key)] = key
    for alias in item.get("aliases", "").split(","):
        alias_key = normalize_curve_name(alias)
        if alias_key:
            _ALIAS_LOOKUP.setdefault(alias_key, key)


@dataclass(frozen=True)
class CurveMnemonicRecord:
    curve_name: str
    canonical: str
    label: str
    group: str
    category: str
    unit: str
    match_type: str
    aliases: str
    recommendation: str


def lookup_curve_mnemonic(curve_name: object) -> CurveMnemonicRecord:
    """Return dictionary metadata for a LAS mnemonic with safe fallbacks."""

    name = normalize_curve_name(curve_name)
    dictionary_key = _ALIAS_LOOKUP.get(name)
    if dictionary_key:
        item = MNEMONIC_DICTIONARY[dictionary_key]
        return CurveMnemonicRecord(
            curve_name=name,
            canonical=item["canonical"],
            label=item["label"],
            group=item["group"],
            category=item["category"],
            unit=item["unit"],
            match_type="dictionary" if name == dictionary_key else "alias",
            aliases=item.get("aliases", ""),
            recommendation="Стандартная мнемоника найдена в словаре.",
        )

    group = suggest_curve_group(name)
    category = suggest_curve_category(name, group=group)
    unit = suggest_curve_unit(name, group=group, category=category)
    return CurveMnemonicRecord(
        curve_name=name,
        canonical=name,
        label=name or "Unknown curve",
        group=group,
        category=category,
        unit=unit,
        match_type="suggested",
        aliases="",
        recommendation="Мнемоника не найдена в словаре: проверьте название и при необходимости задайте alias/группу/единицу вручную.",
    )


def build_curve_mnemonic_records(columns: Iterable[object]) -> tuple[CurveMnemonicRecord, ...]:
    """Build dictionary records for all LAS curves in stable column order."""

    return tuple(lookup_curve_mnemonic(column) for column in columns)


def curve_mnemonic_table_rows(columns: Iterable[object]) -> tuple[dict[str, str], ...]:
    """Return UI rows for mnemonic dictionary review."""

    rows: list[dict[str, str]] = []
    for record in build_curve_mnemonic_records(columns):
        rows.append(
            {
                "curve_name": record.curve_name,
                "canonical": record.canonical,
                "label": record.label,
                "group": record.group,
                "group_label": curve_group_label(record.group) if record.group in CURVE_GROUP_LABELS else record.group,
                "category": record.category,
                "category_label": curve_category_label(record.category),
                "unit": record.unit,
                "unit_label": curve_unit_label(record.unit),
                "match_type": record.match_type,
                "aliases": record.aliases,
                "recommendation": record.recommendation,
            }
        )
    return tuple(rows)


def mnemonic_summary_rows(columns: Iterable[object]) -> tuple[dict[str, str], ...]:
    records = build_curve_mnemonic_records(columns)
    total = len(records)
    dictionary = sum(1 for record in records if record.match_type == "dictionary")
    alias = sum(1 for record in records if record.match_type == "alias")
    suggested = sum(1 for record in records if record.match_type == "suggested")
    return (
        {"metric": "Всего кривых", "value": str(total)},
        {"metric": "Найдено по словарю", "value": str(dictionary)},
        {"metric": "Найдено по alias", "value": str(alias)},
        {"metric": "Требуют проверки", "value": str(suggested)},
    )


def mnemonic_reference_manifest(columns: Iterable[object], *, references: dict[str, Any] | None = None) -> dict[str, Any]:
    updated = dict(references or {})
    updated["curve_mnemonics"] = {row["curve_name"]: row for row in curve_mnemonic_table_rows(columns)}
    return updated
