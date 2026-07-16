# Архитектура конвейера импорта

`ImportWizardState` является неизменяемым JSON-safe контрактом. Допустимые этапы: `select`, `preview`, `configure`, `validate`, `register`, `complete`.

`run_batch_import()` изолирует исключения на уровне отдельного файла. Результат каждого элемента представлен `BatchImportItemResult`.

Quick QC работает только с `MetadataScanResult`. Поставщики не должны загружать полные массивы кривых или сейсмические трассы.

Readiness сохраняется в metadata Dataset Manifest полями `readiness_score`, `readiness_status` и `quick_qc_status`.
