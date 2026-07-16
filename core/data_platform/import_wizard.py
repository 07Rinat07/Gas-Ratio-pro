"""Production import-wizard and batch-import contracts.

The module is UI-agnostic and stores only JSON-safe state. Heavy files and
parser objects never enter the wizard state.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Callable, Iterable, Mapping

from .metadata_scanner import MetadataScanResult

WIZARD_STEPS = ("select", "preview", "configure", "validate", "register", "complete")

@dataclass(frozen=True, slots=True)
class ImportWizardState:
    project_id: str
    step: str = "select"
    source_names: tuple[str, ...] = ()
    format_id: str = ""
    profile_id: str = ""
    preview_dataset_id: str = ""
    registered_dataset_ids: tuple[str, ...] = ()
    error_codes: tuple[str, ...] = ()
    options: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.step not in WIZARD_STEPS:
            raise ValueError(f"unknown import-wizard step: {self.step}")
        object.__setattr__(self, "source_names", tuple(str(x) for x in self.source_names))
        object.__setattr__(self, "registered_dataset_ids", tuple(str(x) for x in self.registered_dataset_ids))
        object.__setattr__(self, "error_codes", tuple(str(x) for x in self.error_codes))
        object.__setattr__(self, "options", dict(self.options))

    def advance(self, step: str, **changes: object) -> "ImportWizardState":
        if step not in WIZARD_STEPS:
            raise ValueError(f"unknown import-wizard step: {step}")
        if WIZARD_STEPS.index(step) < WIZARD_STEPS.index(self.step) and step != "select":
            raise ValueError("wizard cannot move backwards except to select")
        return replace(self, step=step, **changes)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["options"] = dict(self.options)
        return payload

@dataclass(frozen=True, slots=True)
class BatchImportItemResult:
    source_name: str
    status: str
    dataset_id: str = ""
    format_id: str = ""
    readiness_score: int = 0
    error_code: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

@dataclass(frozen=True, slots=True)
class BatchImportResult:
    items: tuple[BatchImportItemResult, ...]

    @property
    def success_count(self) -> int:
        return sum(item.status == "success" for item in self.items)

    @property
    def failed_count(self) -> int:
        return sum(item.status == "failed" for item in self.items)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "gas-ratio-pro/batch-import-result/v1",
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "items": [item.to_dict() for item in self.items],
        }

QuickQCProvider = Callable[[MetadataScanResult], Mapping[str, object]]

def metadata_quick_qc(result: MetadataScanResult) -> dict[str, object]:
    """Conservative metadata-only QC shared by binary and well-log formats."""
    warnings = list(result.warnings)
    errors: list[str] = []
    if not result.complete:
        errors.append(f"{result.format_id}.quick_qc.preview_incomplete")
    metadata = dict(result.metadata)
    if result.format_id == "las":
        if not metadata.get("curve_count"):
            warnings.append("las.quick_qc.curves_missing")
        if metadata.get("depth_monotonic") is False:
            errors.append("las.quick_qc.depth_non_monotonic")
    elif result.format_id in {"dlis", "lis79"}:
        if metadata.get("adapter_available") is False:
            warnings.append(f"{result.format_id}.quick_qc.optional_adapter_unavailable")
    elif result.format_id == "segy":
        if not metadata.get("samples_per_trace"):
            warnings.append("segy.quick_qc.samples_per_trace_missing")
        if not metadata.get("sample_interval_us"):
            warnings.append("segy.quick_qc.sample_interval_missing")
    return {
        "status": "blocked" if errors else "review" if warnings else "ready",
        "warning_codes": sorted(set(str(x) for x in warnings)),
        "error_codes": sorted(set(errors)),
        "warning_count": len(set(warnings)),
        "error_count": len(set(errors)),
        "confidence": "high" if result.complete and not errors else "medium" if result.complete else "low",
    }
