"""Machine-readable audit for the inherited v225.4/v225.5 regression set."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


_ALLOWED_CATEGORIES = {
    "obsolete_version_identity",
    "brittle_ui_source_assertion",
    "visual_contract_rebaseline",
    "architecture_boundary_violation",
    "behavioral_compatibility_gap",
}
_ALLOWED_DISPOSITIONS = {
    "retire",
    "replace_with_behavior_test",
    "rebaseline_after_visual_review",
    "fix_implementation",
}


@dataclass(frozen=True, slots=True)
class LegacyRegressionContract:
    id: str
    nodeid: str
    baseline_release: str
    observed_again_in: str
    category: str
    disposition: str
    severity: str
    rationale: str
    replacement_contract: str
    status: str

    @property
    def valid(self) -> bool:
        return (
            bool(self.id)
            and "::" in self.nodeid
            and self.category in _ALLOWED_CATEGORIES
            and self.disposition in _ALLOWED_DISPOSITIONS
            and bool(self.rationale)
            and bool(self.replacement_contract)
            and self.status == "audited"
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "nodeid": self.nodeid,
            "baseline_release": self.baseline_release,
            "observed_again_in": self.observed_again_in,
            "category": self.category,
            "disposition": self.disposition,
            "severity": self.severity,
            "rationale": self.rationale,
            "replacement_contract": self.replacement_contract,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class LegacyRegressionAuditReport:
    schema: str = "gas-ratio-pro.legacy-regression-audit"
    version: str = "1.0"
    release: str = ""
    baseline_release: str = ""
    expected_count: int = 0
    contracts: tuple[LegacyRegressionContract, ...] = field(default_factory=tuple)
    policy: Mapping[str, bool] = field(default_factory=dict)
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def category_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(item.category for item in self.contracts).items()))

    @property
    def disposition_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(item.disposition for item in self.contracts).items()))

    @property
    def implementation_debt_count(self) -> int:
        return sum(item.disposition == "fix_implementation" for item in self.contracts)

    @property
    def replacement_required_count(self) -> int:
        return sum(item.disposition in {"replace_with_behavior_test", "rebaseline_after_visual_review"} for item in self.contracts)

    @property
    def retired_count(self) -> int:
        return sum(item.disposition == "retire" for item in self.contracts)

    @property
    def ok(self) -> bool:
        nodeids = [item.nodeid for item in self.contracts]
        return (
            self.expected_count == 51
            and len(self.contracts) == self.expected_count
            and len(nodeids) == len(set(nodeids))
            and all(item.valid for item in self.contracts)
            and all(self.policy.get(key) is True for key in (
                "no_silent_xfail",
                "no_test_deletion_without_replacement",
                "architecture_debt_remains_visible",
                "visual_rebaseline_requires_golden_review",
            ))
            and not self.issues
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "release": self.release,
            "baseline_release": self.baseline_release,
            "expected_count": self.expected_count,
            "audited_count": len(self.contracts),
            "category_counts": self.category_counts,
            "disposition_counts": self.disposition_counts,
            "implementation_debt_count": self.implementation_debt_count,
            "replacement_required_count": self.replacement_required_count,
            "retired_count": self.retired_count,
            "policy": dict(self.policy),
            "issues": list(self.issues),
            "ok": self.ok,
            "contracts": [item.to_dict() for item in self.contracts],
        }


class LegacyRegressionAuditService:
    """Load and validate the complete inherited regression catalogue."""

    def load(self, path: Path | str) -> LegacyRegressionAuditReport:
        source = Path(path)
        payload = json.loads(source.read_text(encoding="utf-8"))
        issues: list[str] = []
        if payload.get("schema") != "gas-ratio-pro.legacy-regression-audit":
            issues.append("unsupported_legacy_regression_audit_schema")
        if str(payload.get("version") or "") != "1.0":
            issues.append("unsupported_legacy_regression_audit_version")
        contracts: list[LegacyRegressionContract] = []
        for raw in _mapping_list(payload.get("contracts")):
            contract = LegacyRegressionContract(
                id=str(raw.get("id") or ""),
                nodeid=str(raw.get("nodeid") or ""),
                baseline_release=str(raw.get("baseline_release") or ""),
                observed_again_in=str(raw.get("observed_again_in") or ""),
                category=str(raw.get("category") or ""),
                disposition=str(raw.get("disposition") or ""),
                severity=str(raw.get("severity") or ""),
                rationale=str(raw.get("rationale") or ""),
                replacement_contract=str(raw.get("replacement_contract") or ""),
                status=str(raw.get("status") or ""),
            )
            if not contract.valid:
                issues.append(f"invalid_legacy_regression_contract:{contract.id or contract.nodeid}")
            contracts.append(contract)
        expected = int(payload.get("baseline_failed_count") or 0)
        if expected != len(contracts):
            issues.append(f"legacy_regression_count_mismatch:{expected}:{len(contracts)}")
        nodeids = [item.nodeid for item in contracts]
        if len(nodeids) != len(set(nodeids)):
            issues.append("duplicate_legacy_regression_nodeid")
        return LegacyRegressionAuditReport(
            release=str(payload.get("release") or ""),
            baseline_release=str(payload.get("baseline_release") or ""),
            expected_count=expected,
            contracts=tuple(contracts),
            policy={str(key): bool(value) for key, value in _mapping(payload.get("policy")).items()},
            issues=tuple(dict.fromkeys(issues)),
        )

    def write_summary(self, report: LegacyRegressionAuditReport, path: Path | str) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


__all__ = [
    "LegacyRegressionAuditReport",
    "LegacyRegressionAuditService",
    "LegacyRegressionContract",
]
