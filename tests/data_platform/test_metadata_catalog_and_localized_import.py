import json
import sqlite3

from core.internationalization.localization_service import LocalizationService
from services.data_platform_application_service import DataPlatformApplicationService


def _las(version="1.2") -> str:
    return f"""~V
VERS. {version}
~W
WELL. Legacy-1
STRT.M 1000
STOP.M 1001
STEP.M 0.5
NULL. -999.25
~C
DEPT.M
GR.API
~A
1000 80
1000.5 81
1001 82
"""


def test_registration_projects_manifest_to_sqlite_and_exposes_stable_codes(tmp_path):
    source = tmp_path / "legacy.las"
    source.write_text(_las(), encoding="latin-1")
    service = DataPlatformApplicationService(tmp_path / "projects")

    result = service.register_source_file_result(project_id="project-a", source=source)

    assert "las.validation.legacy_format" in [item.code for item in result.validation_findings]
    snapshot = service.snapshot("project-a")
    assert snapshot["metadata_catalog"]["dataset_count"] == 1
    assert snapshot["metadata_catalog"]["legacy_las_count"] == 1
    database = tmp_path / "projects" / "project-a" / "datasets" / "catalog.sqlite3"
    with sqlite3.connect(database) as connection:
        row = connection.execute("SELECT dataset_id, compatibility_mode, legacy_las FROM datasets").fetchone()
    assert row == (result.manifest.dataset_id, "legacy-pre-2.0", 1)
    json.dumps(snapshot, ensure_ascii=False)


def test_import_result_messages_are_localized_without_changing_codes(tmp_path):
    source = tmp_path / "legacy.las"
    source.write_text(_las(), encoding="latin-1")
    service = DataPlatformApplicationService(tmp_path / "projects")
    result = service.register_source_file_result(project_id="project-a", source=source)
    catalogs = {
        "ru": {
            "import.dataset.success": "ok {source_name}",
            "import.dataset.duplicate": "dup {source_name} {count}",
            "import.dataset.legacy_las": "старый {source_name}",
            "import.dataset.validation_warning": "предупреждения {count}",
            "import.dataset.validation_blocked": "blocked",
        },
        "kk": {
            "import.dataset.success": "ok {source_name}",
            "import.dataset.duplicate": "dup {source_name} {count}",
            "import.dataset.legacy_las": "ескі {source_name}",
            "import.dataset.validation_warning": "ескертулер {count}",
            "import.dataset.validation_blocked": "blocked",
        },
        "en": {
            "import.dataset.success": "ok {source_name}",
            "import.dataset.duplicate": "dup {source_name} {count}",
            "import.dataset.legacy_las": "legacy {source_name}",
            "import.dataset.validation_warning": "warnings {count}",
            "import.dataset.validation_blocked": "blocked",
        },
    }
    localizer = LocalizationService(catalogs, language="kk")

    messages = result.localized_messages(localizer.translate)

    assert messages[0] == "ескі legacy.las"
    assert messages[1].startswith("ескертулер ")
    assert result.to_dict()["validation_codes"] == [item.code for item in result.validation_findings]


def test_legacy_wrap_mode_emits_stable_validation_code(tmp_path):
    source = tmp_path / "wrapped.las"
    source.write_text(_las().replace("VERS. 1.2", "VERS. 1.2\nWRAP. YES"), encoding="latin-1")
    result = DataPlatformApplicationService(tmp_path / "projects").register_source_file_result(
        project_id="project-a", source=source
    )
    assert "las.validation.wrap_yes" in result.to_dict()["validation_codes"]
