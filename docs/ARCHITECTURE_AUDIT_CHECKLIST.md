# Hydrocarbon Interpretation Engine v1.0 Architecture Audit

Итог: **готово к Freeze v1.0** при успешном запуске `run_hydrocarbon_validation_suite()`.

## Проверено

- Единый источник правды для интервалов: `detect_hydrocarbon_intervals`.
- Отчеты, графики и UI должны использовать public payload.
- Evidence, Context, Rule Trace, Explanation, Recommendations и Limitations связаны через модель интервала.
- Литологические перемычки хранятся отдельно как `LithologyBarrier`.
- `Claystone` используется как правильный термин для аргиллита / глинистой породы; `Clay` — для глины.
- Default report payload не содержит служебные row count / NaN / diagnostics.
- Validation Dataset v2 покрывает gas, oil, condensate, Claystone barrier, noisy/uncertain, missing curves.

## Запрещено downstream-модулям

- Повторно классифицировать интервалы внутри отчетов, графиков или UI.
- Объединять продуктивные интервалы через lithology/barrier gaps без явного параметра.
- Показывать технические детали в инженерном отчете по умолчанию.

## Следующий модуль

Professional Reporting System: Executive Summary, interval cards, well log tablet, PDF/DOCX, technical appendix.
