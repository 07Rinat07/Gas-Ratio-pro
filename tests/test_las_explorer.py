from __future__ import annotations

from pathlib import Path

import pytest

from projects import (
    build_project_las_explorer_table,
    create_project,
    diagnose_project_las_file,
    list_project_las_explorer_items,
    preview_project_las_file,
    save_project_las_explorer_settings,
    save_project_las_file,
    search_project_las_explorer_items,
)


def _sample_las_bytes() -> bytes:
    return b"""~Version
VERS. 2.0 : CWLS LOG ASCII STANDARD
WRAP. NO
~Well
WELL. Demo-1 : Well name
NULL. -999.25
~Curve
DEPT.M : Depth
GR.API : Gamma ray
C1.PPM : Methane
~ASCII
1000.0 80 1200
1000.5 82 -999.25
1001.0 79 1300
"""


def test_las_explorer_diagnoses_and_previews_project_las(tmp_path: Path):
    project = create_project(tmp_path, name="LAS Explorer Demo")
    las_file = save_project_las_file(_sample_las_bytes(), tmp_path, project.id, "demo.las", "Demo-1", metadata={"curves": ["DEPT", "GR", "C1"]})

    diagnostics = diagnose_project_las_file(tmp_path, project.id, las_file.id)
    preview = preview_project_las_file(tmp_path, project.id, las_file.id, rows=2)

    assert diagnostics.rows == 3
    assert diagnostics.curves_count == 3
    assert diagnostics.depth_curve == "DEPT"
    assert diagnostics.min_depth == 1000.0
    assert len(preview) == 2


def test_las_explorer_search_tags_favorites_and_table(tmp_path: Path):
    project = create_project(tmp_path, name="LAS Explorer Search")
    las_file = save_project_las_file(_sample_las_bytes(), tmp_path, project.id, "demo.las", "Demo-1", version_label="QA import", metadata={"curves": ["DEPT", "GR", "C1"]})
    save_project_las_explorer_settings(tmp_path, project.id, las_file.id, tags=["QA", "Gas"], favorite=True, note="Check methane", group="North")

    items = list_project_las_explorer_items(tmp_path, project.id, include_diagnostics=True)
    filtered = search_project_las_explorer_items(items, query="methane", tag="gas", favorites_only=True)
    table = build_project_las_explorer_table(filtered)

    assert len(filtered) == 1
    assert filtered[0].favorite is True
    assert filtered[0].tags == ("qa", "gas")
    assert table[0]["Избранное"] == "★"
    assert table[0]["Кривые"] == 3


def test_las_explorer_validates_inputs(tmp_path: Path):
    project = create_project(tmp_path, name="LAS Explorer Validation")
    las_file = save_project_las_file(_sample_las_bytes(), tmp_path, project.id, "demo.las", "Demo-1")

    with pytest.raises(ValueError, match="1..500"):
        preview_project_las_file(tmp_path, project.id, las_file.id, rows=0)

    with pytest.raises(FileNotFoundError):
        save_project_las_explorer_settings(tmp_path, project.id, "missing", tags=["qa"])
