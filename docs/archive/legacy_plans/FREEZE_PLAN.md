# Hydrocarbon Interpretation Engine v1.0 Freeze Plan

Статус: **Frozen / Complete** после прохождения встроенного validation suite.

## Зафиксированные публичные модели

- `HydrocarbonIntervalResult`
- `HydrocarbonInterval`
- `LithologyBarrier`
- `HydrocarbonInterpretationContext`
- `InterpretationExplanation`
- `InterpretationLimitation`
- `InterpretationRecommendation`

## Зафиксированные публичные API

- `detect_hydrocarbon_intervals`
- `build_hydrocarbon_interval_engine_payload`
- `hydrocarbon_interval_table_rows`
- `hydrocarbon_interval_marker_rows`
- `lithology_barrier_table_rows`
- `build_interpretation_explanation`
- `build_interpretation_limitations`
- `build_interpretation_recommendations`
- `run_hydrocarbon_validation_suite`
- `hydrocarbon_engine_freeze_status`

## Definition of Done

- API стабилизирован.
- Validation Dataset v2 подключен.
- Регрессионные сценарии проходят.
- Интервалы через `Claystone barrier` не объединяются автоматически.
- Default payload остается инженерным, без технического мусора.
- Технические детали доступны только через `include_technical=True`.

## Следующий этап

После freeze следующий модуль: **Professional Reporting System**.
