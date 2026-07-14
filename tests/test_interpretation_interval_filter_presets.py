import json

from projects.interpretation_interval_analysis import InterpretationIntervalFilter
from projects.interpretation_interval_filter_presets import (
    FILTER_PRESET_EXCHANGE_SCHEMA,
    InterpretationIntervalFilterPresetRepository,
    export_filter_presets_json,
    import_filter_presets_json,
)


def _criteria(query="gas"):
    return InterpretationIntervalFilter(
        query=query,
        interval_types=("gas",),
        sources=("manual",),
        depth_top=100,
        depth_base=200,
        min_thickness=1,
        max_thickness=20,
    )


def test_repository_crud_and_scope(tmp_path):
    repo = InterpretationIntervalFilterPresetRepository(
        root=tmp_path, project_id="project-a", well_id="well-a"
    )
    preset = repo.save(name="Газовые интервалы", criteria=_criteria())
    assert repo.get(preset.id).criteria == _criteria()
    updated = repo.save(name="Газ", criteria=_criteria("target"), preset_id=preset.id)
    assert updated.id == preset.id
    assert updated.created_at == preset.created_at
    assert repo.list()[0].name == "Газ"
    other = InterpretationIntervalFilterPresetRepository(
        root=tmp_path, project_id="project-a", well_id="well-b"
    )
    assert other.list() == ()
    assert repo.delete(preset.id) is True
    assert repo.delete(preset.id) is False


def test_exchange_round_trip_and_replace(tmp_path):
    repo = InterpretationIntervalFilterPresetRepository(root=tmp_path, project_id="p", well_id="w")
    first = repo.save(name="First", criteria=_criteria())
    second = repo.save(name="Second", criteria=_criteria("water"))
    data = export_filter_presets_json(
        repo.list(), project_id="p", well_id="w", interpretation_id="default"
    )
    payload = json.loads(data)
    assert payload["schema"] == FILTER_PRESET_EXCHANGE_SCHEMA
    imported = import_filter_presets_json(data)
    assert {item.id for item in imported} == {first.id, second.id}
    target = InterpretationIntervalFilterPresetRepository(root=tmp_path, project_id="p", well_id="w2")
    target.replace_all(imported)
    assert [item.name for item in target.list()] == ["First", "Second"]


def test_import_rejects_duplicate_ids():
    repo_data = export_filter_presets_json([], project_id="p", well_id="w", interpretation_id="default")
    payload = json.loads(repo_data)
    # Build one valid preset through the repository-independent public API.
    from projects.interpretation_interval_filter_presets import build_filter_preset
    row = build_filter_preset(name="A", criteria=_criteria()).to_dict()
    payload["presets"] = [row, row]
    try:
        import_filter_presets_json(json.dumps(payload))
    except ValueError as exc:
        assert "UUID" in str(exc)
    else:
        raise AssertionError("ValueError expected")
