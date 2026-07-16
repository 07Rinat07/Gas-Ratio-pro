from __future__ import annotations

from .models import QCReport


def localize_qc_report(report: QCReport, translate) -> dict[str, object]:
    payload = report.to_dict()
    localized = []
    for finding in report.findings:
        text = translate(finding.message_key)
        localized.append({**finding.to_dict(), "message": text if text != finding.message_key else finding.code})
    payload["findings"] = localized
    payload["status_label"] = translate(f"qc.status.{report.status}")
    return payload
