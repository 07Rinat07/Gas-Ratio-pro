from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class MethodProfile:
    """Auditable profile for a published or project-internal calculation method.

    The registry stores only short bibliographic metadata, method scope and
    project usage notes. It must not reproduce copyrighted tables, charts or
    proprietary interpretation plates.
    """

    method_id: str
    name: str
    authors: tuple[str, ...]
    year: str
    source_title: str
    source_type: str
    status: str
    implementation_status: str
    scope: str
    limitations: str
    citation_note: str


METHOD_REGISTRY: Mapping[str, MethodProfile] = {
    "haworth_mud_gas": MethodProfile(
        method_id="haworth_mud_gas",
        name="Haworth mud-gas ratios",
        authors=("Haworth", "Sellens", "Whittaker"),
        year="1985",
        source_title="Interpretation of hydrocarbon shows using light hydrocarbon ratios",
        source_type="published mud-gas interpretation literature",
        status="verified_public_reference",
        implementation_status="implemented",
        scope="Preliminary mud-gas evaluation using wetness, balance and character ratios.",
        limitations=(
            "Requires mud-gas quality control and must be calibrated against logs, tests, "
            "lithology and operational context before final reservoir conclusions."
        ),
        citation_note="Use short formula descriptions only; do not reproduce copyrighted charts or tables.",
    ),
    "pixler_gas_ratio": MethodProfile(
        method_id="pixler_gas_ratio",
        name="Pixler hydrocarbon gas ratios",
        authors=("B. O. Pixler",),
        year="1969",
        source_title="Formation Evaluation by Analysis of Hydrocarbon Ratios",
        source_type="Journal of Petroleum Technology / SPE publication",
        status="verified_public_reference",
        implementation_status="implemented",
        scope="Preliminary fluid-character support using methane-to-heavier-hydrocarbon ratios.",
        limitations=(
            "The method is a supporting mud-gas indicator and must not be used as a standalone "
            "commercial hydrocarbon classifier."
        ),
        citation_note="Cite the publication and implement ratio calculations in original project code.",
    ),
    "project_oil_indicator": MethodProfile(
        method_id="project_oil_indicator",
        name="Project oil/gas indicator",
        authors=("GAS RATIO PRO project",),
        year="2026",
        source_title="Internal engineering indicator derived from calculated gas-ratio fields",
        source_type="project_engineering_hint",
        status="project_engineering_hint",
        implementation_status="implemented_with_warning",
        scope="Supporting preliminary separation of gas/oil tendencies in report payloads.",
        limitations=(
            "Not a published standalone method. It must stay labelled as a project engineering hint "
            "until calibrated and validated on field datasets."
        ),
        citation_note="Report as internal supporting indicator, not as external published method.",
    ),
    "hydrocarbon_interval_engine": MethodProfile(
        method_id="hydrocarbon_interval_engine",
        name="GAS RATIO PRO Hydrocarbon Interval Engine",
        authors=("GAS RATIO PRO project",),
        year="2026",
        source_title="Project rule engine combining sourced mud-gas evidence, quality flags and lithology barriers",
        source_type="internal_project_engine",
        status="project_engineering_hint",
        implementation_status="active_development",
        scope="Grouping, classification, evidence packaging and confidence scoring of interpreted intervals.",
        limitations=(
            "Does not prove productivity or reserves. Output is an engineering interpretation model "
            "that requires validation against logs, tests and geological context."
        ),
        citation_note="Document public formula sources used by the engine and keep project rules explicit.",
    ),
}


PARAMETER_METHOD_MAP: Mapping[str, str] = {
    "wh": "haworth_mud_gas",
    "bh": "haworth_mud_gas",
    "ch": "haworth_mud_gas",
    "c1/c2": "pixler_gas_ratio",
    "c1/c3": "pixler_gas_ratio",
    "c1/c4": "pixler_gas_ratio",
    "c1/c5": "pixler_gas_ratio",
    "oil indicator": "project_oil_indicator",
    "text interpretation": "hydrocarbon_interval_engine",
    "fluid_type": "hydrocarbon_interval_engine",
}


def get_method_profile(method_id: str) -> MethodProfile:
    """Return a registered method profile or raise a clear error."""

    try:
        return METHOD_REGISTRY[method_id]
    except KeyError as exc:
        raise KeyError(f"Calculation method is not registered: {method_id}") from exc


def method_id_for_parameter(parameter: str, fallback: str = "hydrocarbon_interval_engine") -> str:
    """Resolve a parameter name to its registered method id."""

    return PARAMETER_METHOD_MAP.get(str(parameter).strip().lower(), fallback)


def method_registry_rows() -> tuple[dict[str, object], ...]:
    """Return serializable method registry rows for UI/report diagnostics."""

    return tuple(profile.__dict__ for profile in METHOD_REGISTRY.values())
