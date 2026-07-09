# Hydrocarbon Interval Engine v12 — Validation and API Contract

## Назначение

v12 добавляет контрольный слой для завершения Hydrocarbon Interval Engine перед переходом к Professional Reporting System.

Главная цель: изменения в формулах, правилах или визуализации не должны незаметно ломать уже согласованные практические сценарии интерпретации.

## Что добавлено

- `HydrocarbonValidationCase` — описание эталонного сценария проверки.
- `HydrocarbonValidationResult` — результат проверки движка на эталонном сценарии.
- `validate_hydrocarbon_interval_result()` — регрессионная проверка результата.
- `hydrocarbon_validation_result_rows()` — табличный экспорт результатов QA.
- `hydrocarbon_engine_api_contract()` — публичный контракт движка для отчетов, графиков, UI и экспорта.

## Инженерное правило

Hydrocarbon Interval Engine остается единственным источником истины для:

- интервалов УВ;
- литологических перемычек;
- confidence;
- rule trace;
- evidence;
- provenance.

Report, Plot, PDF, DOCX и UI-слои не должны заново классифицировать интервалы.

## Практические validation cases

Минимальный набор для v1.0:

1. Вероятный газовый интервал.
2. Вероятный нефтяной интервал.
3. Газоконденсатный интервал.
4. Переходная зона.
5. Интервалы, разделенные Claystone barrier.
6. Одиночный всплеск, требующий проверки.
7. Интервал с недостатком данных.
8. Шумные данные с пропусками.

## Report/UI policy

Технические сведения (`row count`, `NaN`, `source_start_row`, `rule_traces`, `provenance`) не должны попадать на первую страницу инженерного отчета. Они допустимы только в экспертном режиме или техническом приложении.

## Статус

Hydrocarbon Interval Engine близок к закрытию v1.0. После v12 остаются:

- финальное расширение validation dataset;
- проверка на реальных LAS;
- freeze API;
- переход к Professional Reporting System.
