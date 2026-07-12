from pathlib import Path

from core.reservoir_passport import ReservoirMethodResult, ReservoirPassport
from core.reservoir_ranking import (
    DEFAULT_RANKING_PROFILE,
    ReservoirRankingProfile,
    ReservoirRankingWeights,
    build_reservoir_rank,
    compare_reservoir_rankings,
)
from projects.reservoir_ranking_profiles import load_project_ranking_profiles, save_project_ranking_profiles


def _passport(interval_id="HC-001", **overrides):
    values = dict(
        interval_id=interval_id, top=1000.0, base=1010.0, thickness=10.0,
        fluid_type="oil", confidence_score=80, data_confidence_score=80,
        geological_confidence_score=70, decision_level="medium",
        gas_composition=(), derived_metrics=(),
        methods=(ReservoirMethodResult("Pixler", "oil", 80, "Доступно"),),
        agreement_percent=75.0, data_completeness_percent=85.0,
        limitations=(), recommendations=(), engineering_conclusion="Oil candidate",
        ready_for_report=True, readiness_label="Готов к инженерному отчёту",
    )
    values.update(overrides)
    return ReservoirPassport(**values)


def test_weights_are_normalized_to_one_hundred():
    weights = ReservoirRankingWeights(10, 20, 30, 40).normalized()
    assert round(sum((weights.confidence, weights.agreement, weights.completeness, weights.thickness)), 6) == 100


def test_custom_profile_changes_score_breakdown():
    custom = ReservoirRankingProfile(
        "custom", "Custom", ReservoirRankingWeights(50, 20, 10, 20), 20.0
    )
    standard = build_reservoir_rank(_passport(), profile=DEFAULT_RANKING_PROFILE)
    changed = build_reservoir_rank(_passport(), profile=custom)
    assert changed.confidence_component > standard.confidence_component
    assert changed.agreement_component < standard.agreement_component


def test_profile_round_trip(tmp_path: Path):
    profile = ReservoirRankingProfile(
        "custom-test", "Полевой профиль", ReservoirRankingWeights(40, 30, 20, 10), 12.5
    )
    save_project_ranking_profiles((profile,), root=tmp_path, project_id="default")
    loaded = load_project_ranking_profiles(root=tmp_path, project_id="default")
    assert loaded[0].name == "Полевой профиль"
    assert loaded[0].reference_thickness == 12.5
    assert loaded[0].weights.confidence == 40


def test_comparison_explains_rank_and_score_change():
    old_item = build_reservoir_rank(_passport(), profile=DEFAULT_RANKING_PROFILE)
    old_item = type(old_item)(**{**old_item.__dict__}) if hasattr(old_item, "__dict__") else old_item
    # dataclass uses slots; create ranked copies explicitly.
    from dataclasses import asdict
    old_item = type(old_item)(**{**asdict(old_item), "rank": 1})
    custom = ReservoirRankingProfile("custom", "Custom", ReservoirRankingWeights(50, 20, 10, 20), 20.0)
    new_item = build_reservoir_rank(_passport(), profile=custom)
    new_item = type(new_item)(**{**asdict(new_item), "rank": 2})
    change = compare_reservoir_rankings((old_item,), (new_item,), previous_profile=DEFAULT_RANKING_PROFILE, current_profile=custom)[0]
    assert change.rank_delta == -1
    assert "Изменение весов" in change.explanation
