from pathlib import Path
import json

from core.data_platform import (
    ImportPreviewCache,
    ImportProfile,
    compute_readiness_score,
)
from services.data_platform_application_service import DataPlatformApplicationService


def _las(path: Path) -> None:
    path.write_text(
        "~Version\nVERS. 2.0\n~Well\nWELL. Demo\nSTRT.M 1000\nSTOP.M 1001\nSTEP.M 0.5\nNULL. -999.25\n~Curve\nDEPT.M\nGR.API\n~ASCII\n1000 50\n1000.5 51\n",
        encoding="utf-8",
    )


def test_capability_matrix_is_json_safe(tmp_path):
    service = DataPlatformApplicationService(tmp_path)
    matrix = service.capability_matrix()
    assert matrix["schema"].endswith("v1")
    rows = {row["format_id"]: row for row in matrix["formats"]}
    assert rows["las"]["metadata_preview"] is True
    assert rows["segy"]["streaming"] is True
    json.dumps(matrix)


def test_preview_cache_uses_checksum_profile_and_scanner_version(tmp_path):
    source = tmp_path / "well.las"
    _las(source)
    service = DataPlatformApplicationService(tmp_path / "projects")
    profile = ImportProfile("las-modern", "LAS Modern", "las", scanner_version="2")
    first = service.build_import_preview(source, profile=profile)
    second = service.build_import_preview(source, profile=profile)
    assert first["cache"]["hit"] is False
    assert second["cache"]["hit"] is True
    assert first["cache"]["key"] == second["cache"]["key"]
    assert 0 <= first["readiness"]["score"] <= 100


def test_import_profiles_are_project_scoped_and_atomic(tmp_path):
    service = DataPlatformApplicationService(tmp_path)
    profile = ImportProfile("las-legacy", "LAS Legacy", "las", options={"mode": "tolerant"})
    result = service.save_import_profile("project-a", profile)
    assert result["profile"]["options"]["mode"] == "tolerant"
    listed = service.list_import_profiles("project-a")
    assert listed == (profile.to_dict(),)
    assert service.list_import_profiles("project-b") == ()


def test_readiness_is_explainable_and_bounded():
    ready = compute_readiness_score(preview_complete=True, warning_count=0, metadata_field_count=10, qc_available=True)
    blocked = compute_readiness_score(preview_complete=False, warning_count=5, error_count=2, metadata_field_count=1)
    assert ready["status"] == "ready"
    assert blocked["status"] == "blocked"
    assert ready["score"] > blocked["score"]


def test_preview_cache_is_lru_and_json_copy_safe():
    cache = ImportPreviewCache(max_entries=1)
    cache.put("a", {"nested": {"value": 1}})
    payload = cache.get("a")
    payload["nested"]["value"] = 99
    assert cache.get("a")["nested"]["value"] == 1
    cache.put("b", {"value": 2})
    assert cache.get("a") is None
