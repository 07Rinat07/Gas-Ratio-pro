import json
from pathlib import Path
import pandas as pd

from core.qc import LasQCEngine, QC_SCHEMA, localize_qc_report
from services.qc_application_service import QCApplicationService


def _df():
    df = pd.DataFrame({
        "DEPT": [1000.0, 1000.5, 1000.5, 1002.0],
        "GR": [80.0, -1.0, 320.0, -999.25],
        "RHOB": [2.3, 2.4, 2.5, 2.6],
    })
    df.attrs["las_units"] = {"GR": "GAPI", "RHOB": "G/C3"}
    return df


def test_engine_emits_stable_codes_and_json_safe_statistics():
    report = LasQCEngine().run(_df(), expected_step=0.5)
    payload = report.to_dict()
    codes = {item["code"] for item in payload["findings"]}
    assert report.schema == QC_SCHEMA
    assert "QC-DEPTH-004" in codes
    assert "QC-DEPTH-006" in codes
    assert "QC-NULL-001" in codes
    assert payload["curve_statistics"]
    json.dumps(payload)


def test_localized_report_keeps_machine_codes_stable():
    report = LasQCEngine().run(_df(), expected_step=0.5)
    translations = {"qc.status.failed": "Проверка не пройдена", "qc.status.warning": "Есть предупреждения"}
    payload = localize_qc_report(report, lambda key: translations.get(key, f"T:{key}"))
    assert payload["findings"][0]["code"].startswith("QC-")
    assert payload["findings"][0]["message"].startswith("T:qc.finding.")


def test_application_service_is_reusable():
    service = QCApplicationService()
    report = service.run_las(_df(), expected_step=0.5)
    assert report.dataset_kind == "las"


def test_documentation_manifest_has_all_three_languages():
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((root / "docs/documentation_manifest.json").read_text(encoding="utf-8"))
    for document in manifest["documents"]:
        assert set(document["languages"]) == {"ru", "kk", "en"}
        for relative in document["languages"].values():
            path = root / "docs" / relative
            assert path.exists() and path.read_text(encoding="utf-8").strip()


def test_application_container_reuses_qc_service():
    from core.application_service_container import ApplicationServiceContainer
    from core.runtime_service_registry import RuntimeServiceRegistry
    container = ApplicationServiceContainer(RuntimeServiceRegistry(), {})
    assert container.quality_control() is container.quality_control()
