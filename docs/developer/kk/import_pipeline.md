# Импорт конвейерінің архитектурасы

`ImportWizardState` — өзгермейтін және JSON-safe келісімшарт. Рұқсат етілген кезеңдер: `select`, `preview`, `configure`, `validate`, `register`, `complete`.

`run_batch_import()` әр файлдың қатесін бөлек оқшаулайды. Әр элементтің нәтижесі `BatchImportItemResult` арқылы беріледі.

Quick QC тек `MetadataScanResult` деректерімен жұмыс істейді. Провайдерлер қисықтардың толық массивтерін немесе сейсмикалық трассаларды жүктемеуі тиіс.

Readiness Dataset Manifest metadata ішінде `readiness_score`, `readiness_status` және `quick_qc_status` өрістерімен сақталады.
