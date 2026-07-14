import json
from pathlib import Path
from uuid import UUID

import pytest

from projects.interpretation_intervals import (
    INTERPRETATION_INTERVALS_SCHEMA,
    create_interpretation_interval,
    delete_interpretation_interval,
    interpretation_interval_table_rows,
    load_interpretation_intervals,
    update_interpretation_interval,
)


def test_create_persists_uuid_and_project_well_interpretation_hierarchy(tmp_path: Path):
    created = create_interpretation_interval(
        root=tmp_path,
        project_id="project-1",
        well_id="well-1",
        interpretation_id="primary",
        label="Газонасыщенный пласт",
        top=1000.0,
        base=1012.5,
        interval_type="gas",
        color="#FFAA00",
        comment="Проверить по каротажу",
    )

    UUID(created.id)
    storage = tmp_path / "project-1" / "wells" / "well-1" / "interpretations" / "primary" / "intervals.json"
    assert storage.exists()
    payload = json.loads(storage.read_text(encoding="utf-8"))
    assert payload["schema"] == INTERPRETATION_INTERVALS_SCHEMA
    assert payload["intervals"][0]["id"] == created.id

    restored = load_interpretation_intervals(tmp_path, "project-1", "well-1", "primary")
    assert restored.intervals == (created,)
    assert restored.intervals[0].thickness == 12.5
    assert restored.intervals[0].middle_depth == 1006.25


def test_update_preserves_uuid_and_created_at(tmp_path: Path):
    created = create_interpretation_interval(
        root=tmp_path,
        project_id="project-1",
        well_id="well-1",
        label="A",
        top=100.0,
        base=110.0,
    )
    updated = update_interpretation_interval(
        created.id,
        root=tmp_path,
        project_id="project-1",
        well_id="well-1",
        label="A edited",
        top=101.0,
        base=115.0,
        interval_type="oil",
        color="#112233",
        comment="edited",
    )

    assert updated.id == created.id
    assert updated.created_at == created.created_at
    assert updated.label == "A edited"
    assert load_interpretation_intervals(tmp_path, "project-1", "well-1").intervals == (updated,)


def test_delete_is_idempotent(tmp_path: Path):
    created = create_interpretation_interval(
        root=tmp_path,
        project_id="project-1",
        well_id="well-1",
        label="A",
        top=100.0,
        base=110.0,
    )
    assert delete_interpretation_interval(
        created.id, root=tmp_path, project_id="project-1", well_id="well-1"
    ) is True
    assert delete_interpretation_interval(
        created.id, root=tmp_path, project_id="project-1", well_id="well-1"
    ) is False
    assert load_interpretation_intervals(tmp_path, "project-1", "well-1").intervals == ()


def test_validation_rejects_invalid_depth_and_color(tmp_path: Path):
    with pytest.raises(ValueError, match="Верх интервала"):
        create_interpretation_interval(
            root=tmp_path, project_id="project-1", well_id="well-1", label="A", top=110.0, base=100.0
        )
    with pytest.raises(ValueError, match="HEX"):
        create_interpretation_interval(
            root=tmp_path,
            project_id="project-1",
            well_id="well-1",
            label="A",
            top=100.0,
            base=110.0,
            color="#GGGGGG",
        )


def test_table_rows_expose_derived_properties(tmp_path: Path):
    created = create_interpretation_interval(
        root=tmp_path,
        project_id="project-1",
        well_id="well-1",
        label="A",
        top=10.0,
        base=14.0,
    )
    rows = interpretation_interval_table_rows((created,))
    assert rows[0]["thickness"] == 4.0
    assert rows[0]["middle_depth"] == 12.0
