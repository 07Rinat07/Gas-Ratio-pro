from pathlib import Path

from services.legacy_regression_audit import LegacyRegressionAuditService

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "legacy_regression_contracts_v225_7.json"


def test_all_51_inherited_regressions_remain_individually_tracked():
    report = LegacyRegressionAuditService().load(REGISTRY)
    assert report.ok is True
    assert len(report.contracts) == 51
    assert sum(report.category_counts.values()) == 51
    assert sum(report.disposition_counts.values()) == 51
    assert all(contract.rationale and contract.replacement_contract for contract in report.contracts)


def test_v225_7_resolves_architecture_source_and_visual_contracts_without_xfail():
    report = LegacyRegressionAuditService().load(REGISTRY)
    assert report.policy["no_silent_xfail"] is True
    assert report.policy["resolved_contracts_keep_original_nodeid"] is True
    assert report.resolved_count == 51
    assert report.active_count == 0
    assert report.implementation_debt_count == 0
    assert report.replacement_required_count == 0
    assert report.retired_count == 0


def test_audit_summary_is_machine_readable(tmp_path):
    service = LegacyRegressionAuditService()
    report = service.load(REGISTRY)
    path = service.write_summary(report, tmp_path / "legacy-regression-audit-summary.json")
    text = path.read_text(encoding="utf-8")
    assert '"audited_count": 51' in text
    assert '"resolved_count": 51' in text
    assert '"active_count": 0' in text
