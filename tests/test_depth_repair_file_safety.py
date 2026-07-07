from __future__ import annotations

from pathlib import Path

from las_editor.depth_repair import create_depth_repair_file_copies


def test_create_depth_repair_file_copies_preserves_original(tmp_path: Path):
    original = tmp_path / "well_01.las"
    original.write_text("~Version\nVERS. 2.0\n~ASCII\n101 1\n100 2\n", encoding="utf-8")
    workspace = tmp_path / "workspace"

    manifest = create_depth_repair_file_copies(original, workspace)

    backup = Path(manifest["backup_path"])
    working = Path(manifest["working_path"])
    assert original.read_text(encoding="utf-8") == "~Version\nVERS. 2.0\n~ASCII\n101 1\n100 2\n"
    assert backup.exists()
    assert working.exists()
    assert backup.read_text(encoding="utf-8") == original.read_text(encoding="utf-8")
    assert working.read_text(encoding="utf-8") == original.read_text(encoding="utf-8")
    assert manifest["original_data_mutated"] is False
