import json
from pathlib import Path

from services.data_platform_application_service import DataPlatformApplicationService


def _segy_fixture(path: Path) -> None:
    textual = (b"C 1 SYNTHETIC" + b" " * 3187)[:3200]
    binary = bytearray(400)
    binary[16:18] = (2000).to_bytes(2, "big")
    binary[20:22] = (10).to_bytes(2, "big")
    binary[24:26] = (5).to_bytes(2, "big")
    binary[300:302] = (0x0201).to_bytes(2, "big")
    path.write_bytes(textual + bytes(binary))


def test_import_preview_is_persisted_as_immutable_preview_dataset(tmp_path):
    source = tmp_path / "cube.sgy"
    _segy_fixture(source)
    service = DataPlatformApplicationService(tmp_path / "projects")
    manifest = service.persist_import_preview(project_id="project-a", source=source, actor="tester", format_id="segy")
    assert manifest.provenance.operation == "metadata-preview"
    assert manifest.metadata["dataset_kind"] == "metadata-preview"
    artifact = service.artifacts.resolve(project_id="project-a", relative_path=manifest.artifact_path)
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["schema"] == "gas-ratio-pro/import-preview/v1"
    assert payload["preview"]["format_id"] == "segy"


def test_dlis_selection_projection_is_safe_without_optional_adapter(tmp_path):
    source = tmp_path / "sample.dlis"
    source.write_bytes(b"synthetic fixture")
    service = DataPlatformApplicationService(tmp_path / "projects")
    projection = service.build_dlis_selection_projection(source, format_id="dlis")
    assert projection["format_id"] == "dlis"
    assert isinstance(projection["logical_files"], list)
    assert "adapter_available" in projection
