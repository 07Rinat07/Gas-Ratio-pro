from core.reservoir_passport import ReservoirPassport, ReservoirMethodResult
from core.reservoir_ranking import build_reservoir_rank, reservoir_ranking_dataframe


def _passport(**overrides):
    values = dict(
        interval_id="HC-001", top=1000.0, base=1010.0, thickness=10.0,
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


def test_priority_score_has_transparent_components():
    item = build_reservoir_rank(_passport())
    assert item.priority_score == 73.5
    assert item.confidence_component == 24.0
    assert item.agreement_component == 22.5
    assert item.completeness_component == 17.0
    assert item.thickness_component == 10.0
    assert item.penalty == 0.0


def test_zero_thickness_is_penalized_and_not_presented_as_reservoir():
    item = build_reservoir_rank(_passport(thickness=0.0, ready_for_report=False))
    assert item.penalty == 20.0
    assert item.priority_score < 60
    assert "одиночная" in item.recommendation.lower()


def test_ranking_dataframe_contains_engineering_columns():
    frame = reservoir_ranking_dataframe((build_reservoir_rank(_passport()),))
    assert {"ID", "Индекс приоритета", "Класс", "Рекомендация"}.issubset(frame.columns)
