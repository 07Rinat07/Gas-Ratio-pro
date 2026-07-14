from pathlib import Path

import pytest

from projects.interpretation_interval_manager import (
    InterpretationIntervalManager,
    InterpretationIntervalOverlapError,
)
from projects.interpretation_interval_properties import (
    InterpretationIntervalPropertiesService,
    interval_properties,
    validate_interval_property_changes,
)


def _service(tmp_path: Path, state: dict):
    manager = InterpretationIntervalManager(
        state,
        root=tmp_path,
        project_id="project-1",
        well_id="well-1",
        interpretation_id="primary",
    )
    return manager, InterpretationIntervalPropertiesService(manager)


def test_properties_projection_contains_editable_and_derived_values(tmp_path: Path):
    manager, service = _service(tmp_path, {})
    created = manager.create(
        label="Layer A",
        top=100.0,
        base=112.0,
        interval_type="reservoir",
        color="#112233",
        comment="Initial",
    )

    properties = service.get(created.id)

    assert properties.interval_id == created.id
    assert properties.thickness == 12.0
    assert properties.middle_depth == 106.0
    assert properties.to_form_values()["color"] == "#112233"


def test_partial_property_changes_preserve_omitted_fields(tmp_path: Path):
    manager, service = _service(tmp_path, {})
    created = manager.create(
        label="Layer A",
        top=100.0,
        base=112.0,
        interval_type="reservoir",
        color="#112233",
        comment="Initial",
    )

    updated = service.apply(created.id, {"base": 118.0, "comment": "Reviewed", "ui_flag": True})

    assert updated.label == "Layer A"
    assert updated.top == 100.0
    assert updated.base == 118.0
    assert updated.thickness == 18.0
    assert updated.middle_depth == 109.0
    assert updated.comment == "Reviewed"
    assert updated.interval_type == "reservoir"


def test_property_changes_use_canonical_validation(tmp_path: Path):
    manager, _ = _service(tmp_path, {})
    created = manager.create(label="Layer A", top=100.0, base=112.0)

    with pytest.raises(ValueError, match="Верх интервала"):
        validate_interval_property_changes(created, {"top": 120.0})

    with pytest.raises(ValueError, match="HEX"):
        validate_interval_property_changes(created, {"color": "#GGGGGG"})


def test_property_apply_can_reject_overlaps_and_remains_undoable(tmp_path: Path):
    manager, service = _service(tmp_path, {})
    first = manager.create(label="A", top=100.0, base=110.0)
    manager.create(label="B", top=120.0, base=130.0)

    with pytest.raises(InterpretationIntervalOverlapError):
        service.apply(first.id, {"top": 125.0, "base": 135.0}, reject_overlaps=True)

    updated = service.apply(first.id, {"top": 105.0, "base": 115.0})
    assert updated.top == 105.0
    assert manager.undo() is True
    assert interval_properties(manager.get_interval(first.id)).top == 100.0
