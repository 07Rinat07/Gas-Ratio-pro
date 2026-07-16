from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

QC_SCHEMA = "gas-ratio-pro/qc-report/v1"


@dataclass(frozen=True, slots=True)
class QCFinding:
    code: str
    severity: str
    message_key: str
    curve: str = ""
    row: int | None = None
    depth: float | None = None
    value: float | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        item = asdict(self)
        item["details"] = dict(self.details)
        return item


@dataclass(frozen=True, slots=True)
class CurveQCStatistics:
    curve: str
    count: int
    valid_count: int
    null_count: int
    null_fraction: float
    minimum: float | None
    maximum: float | None
    mean: float | None
    standard_deviation: float | None
    unique_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class QCReport:
    dataset_kind: str
    generated_at: str
    row_count: int
    curve_count: int
    depth_curve: str
    status: str
    findings: tuple[QCFinding, ...]
    curve_statistics: tuple[CurveQCStatistics, ...]
    schema: str = QC_SCHEMA

    @classmethod
    def create(cls, **kwargs: Any) -> "QCReport":
        return cls(generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), **kwargs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "dataset_kind": self.dataset_kind,
            "generated_at": self.generated_at,
            "row_count": self.row_count,
            "curve_count": self.curve_count,
            "depth_curve": self.depth_curve,
            "status": self.status,
            "summary": {
                "finding_count": len(self.findings),
                "error_count": sum(1 for item in self.findings if item.severity == "error"),
                "warning_count": sum(1 for item in self.findings if item.severity == "warning"),
            },
            "findings": [item.to_dict() for item in self.findings],
            "curve_statistics": [item.to_dict() for item in self.curve_statistics],
        }
