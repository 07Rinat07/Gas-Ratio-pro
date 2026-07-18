# Операторлық калибрлеу пакеттерінің архитектурасы — revision 1

## Stage 5.2 шекарасы

Stage 5.2 деректер мен evidence қосады, бірақ production formulas өзгертпейді; package ішінде `formula_changes=false` міндетті. Әдістер тек `core.petrophysical_method_executor` және numerical validation gate арқылы орындалады.


Пакеттің machine-readable schema мәні: `gas-ratio-pro/operator-calibration-package/v1`.

## Қабаттар

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

UI package repository-ді тікелей оқымайды және жазбайды.

## Fingerprints және сақтау

`package_fingerprint` — fingerprint өрісі алынған канондық manifest SHA-256 мәні. Registry/dataset үшін жеке SHA-256 және өлшем жазылады. `rights_fingerprint` құқық өзгерісін бөлек бекітеді.

Әр пайдалану кезінде сақталған файлдар қайта тексеріледі. `package_id + version` басқа fingerprint-пен қолданылса, version conflict пайда болады.

Repository `data/projects/<project>/petrophysics/operator_calibration/` ішінде packages, comparisons және authorizations болып бөлінеді. Жеке оператор пакеттері релиз архивіне қосылмайды.

## Data-rights gate

Project scope, legal basis, processing және derivative-analysis рұқсаттары міндетті. `final_report_use_allowed` финалдық экспорт алдында қайта тексеріледі. Мерзімі өткен құқықтар пакетті бұғаттайды.

## Comparison және authorization

Comparison бірнеше case нәтижесін method ID бойынша агрегаттап, error metrics пен uncertainty width delta мәндерін шығарады. Project authorization package validation gate, baseline/operator calibration gate, comparison ID, source fingerprint және method decisions мәндерін сақтайды. `blocked_final_report` саясаты өзгермейді.

## Cache isolation

Authorization немесе rights fingerprint өзгерсе, жоба model/artifact cache рендерге дейін тазартылады.
