# Архитектура операторских калибровочных пакетов — revision 1

## Граница Stage 5.2

Stage 5.2 добавляет данные и evidence, но не меняет production formulas. Метод может исполняться только через `core.petrophysical_method_executor` и существующий numerical validation gate.


Machine-readable schema пакета: `gas-ratio-pro/operator-calibration-package/v1`.

## Слои

```text
Professional Print Center
        ↓
OperatorCalibrationPackageApplicationService
        ├── ZIP/data-rights/fingerprint validation
        ├── immutable project repository
        ├── PetrophysicalCalibrationApplicationService
        ├── calibration comparison
        └── project authorization package
        ↓
PresentationExportRuntimeApplicationService
        ↓
ExportController / renderer
```

UI не читает и не записывает package repository напрямую.

## Формат и fingerprint

`package_fingerprint` — SHA-256 канонического manifest без самого поля fingerprint. Manifest содержит SHA-256 и точный размер registry/dataset. `rights_fingerprint` вычисляется отдельно, поэтому изменение разрешений меняет authorization context даже при одинаковых числах.

При каждом использовании сохранённые файлы повторно сверяются с manifest. Пара `package_id + version` immutable: другой fingerprint считается version conflict.

## Repository

```text
data/projects/<project>/petrophysics/operator_calibration/
  package_index.json
  active_package.json
  packages/<package_id>/<version>/<fingerprint>/
    source_package.zip
    manifest.json
    calibration_registry.json
    calibration_dataset.json
    calibration_evidence.json
    import_record.json
  comparisons/<comparison_id>.json
  authorizations/<package_id>/<version>/<authorization_package_id>.json
```

Private operator packages не попадают в пользовательский релизный ZIP.

## Data-rights gate

Import boundary требует project scope, legal basis, processing permission и derivative-analysis permission. `final_report_use_allowed` применяется отдельно непосредственно перед финальным экспортом. Expiration проверяется и при импорте, и при последующем использовании.

## Comparison

Comparison агрегирует несколько cases одного method ID и сопоставляет RMSE, MAE, bias, maximum error и uncertainty width. Результат детерминированно идентифицируется `comparison_id`. Сравнение является evidence, а не механизмом автоматической настройки формул.

## Project authorization package

Для каждого экспорта формируется детерминированный package с:

- project ID;
- method IDs;
- validation и baseline/operator calibration gate IDs;
- comparison ID;
- source package/version/fingerprint;
- rights fingerprint;
- решением по каждому методу.

Методы, покрытые активным operator package, используют его calibration и rights. Остальные методы используют утверждённый project baseline. `blocked_final_report` никогда не обходится.

## Cache isolation

Runtime отслеживает authorization ID, authorization package ID, operator fingerprint и rights fingerprint. При смене контекста model/artifact cache проекта очищается до рендера, чтобы файл предыдущей калибровки не использовался повторно.

## Безопасность ZIP

Разрешены только три root members, ограничены общий и индивидуальный размеры, запрещены каталоги, абсолютные пути и path traversal. Checksums проверяются до запуска production methods.
