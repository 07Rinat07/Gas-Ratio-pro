from pathlib import Path

from services.legacy_regression_audit import LegacyRegressionAuditService

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "legacy_regression_contracts_v225_6.json"


def test_all_51_inherited_regressions_are_individually_classified():
    report = LegacyRegressionAuditService().load(REGISTRY)
    assert report.ok is True
    assert len(report.contracts) == 51
    assert sum(report.category_counts.values()) == 51
    assert sum(report.disposition_counts.values()) == 51
    assert all(contract.rationale and contract.replacement_contract for contract in report.contracts)


def test_audit_does_not_hide_architecture_debt_or_silently_xfail():
    report = LegacyRegressionAuditService().load(REGISTRY)
    assert report.policy["no_silent_xfail"] is True
    assert report.policy["architecture_debt_remains_visible"] is True
    assert report.implementation_debt_count > 0
    assert report.replacement_required_count > 0
    assert report.retired_count > 0


def test_audit_summary_is_machine_readable(tmp_path):
    service = LegacyRegressionAuditService()
    report = service.load(REGISTRY)
    path = service.write_summary(report, tmp_path / "legacy-regression-audit-summary.json")
    assert path.exists()
    assert '"audited_count": 51' in path.read_text(encoding="utf-8")
