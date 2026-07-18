# GAS RATIO PRO

Профессиональная трёхъязычная инженерная платформа для импорта, контроля качества, управления версиями, анализа, интерпретации и визуализации скважинных, геолого-геофизических и проектных данных нефтегазовой отрасли.

**Язык:** Русский · [Қазақша](README.kk.md) · [English](README.en.md)

## Документация

- [Пользовательское руководство](docs/user/ru/index.md)
- [Документация разработчика](docs/developer/ru/index.md)
- [Поддерживаемые форматы](docs/user/ru/supported_formats_and_legal_sources.md)
- [План проекта](docs/project/PROJECT_PLAN.ru.md)
- [Текущий статус](docs/PROJECT_STATUS.ru.md)

## Поддерживаемые и развиваемые форматы

- **LAS 1.x/2.x/3.x** — импорт, legacy compatibility, редактирование, QC, версии, визуализация и экспорт;
- **Excel/CSV** — импорт, mapping, расчёты и визуализация;
- **DLIS/LIS79** — metadata preview через optional `dlisio` adapter;
- **SEG-Y** — header preview, trace-header inventory и geometry diagnostics;
- **PDF/DOCX** — инженерные и QC-отчёты;
- **GeoPackage/Shapefile/GeoTIFF, GRDECL/RESQML, HDF5/NetCDF** — следующие этапы Data/GIS/Reservoir Platform.

## Основные подсистемы

- Workbench и Project Explorer;
- Unified Import Pipeline, профили импорта и readiness score;
- Data Platform: immutable artifacts, Dataset Manifest, SHA-256, provenance и lineage;
- LAS QC Platform и локализованные PDF/DOCX-отчёты;
- газогеохимические расчёты и интерпретация интервалов;
- корреляция скважин и подготовка к многоскважинным планшетам;
- интерфейс и документация на русском, казахском и английском языках.

## Stable-релиз v225.11

- завершён Stage 5.2 Operator Dataset Import & Calibration Comparison;
- добавлен project-scoped импорт операторских ZIP-пакетов с проверкой прав на данные, project scope, checksum и method-registry fingerprint;
- исходный пакет и его manifest/registry/dataset сохраняются неизменяемо с SHA-256 fingerprints;
- доступны сравнения baseline/operator и operator/operator по 10 методам;
- активный пакет участвует в авторизации до создания финального отчёта;
- export artifact и история v5 сохраняют authorization package ID и operator calibration fingerprint;
- Professional Print Center получил трёхъязычную панель импорта, активации, сравнения и диагностики;
- production formulas не изменялись, foundation Dual Water остаётся `blocked_final_report`;
- частные операторские данные не входят в релизный архив;
- запуск gate: `python scripts/run_petrophysical_stage_5_2_gate.py`;
- [инструкция](docs/user/ru/operator_calibration_packages.md) · [архитектура](docs/developer/ru/operator_calibration_package_architecture.md).

- Итоговая проверка v225.11: **2915 passed, 0 failed**; Live Workbench Acceptance: **14/14**; импорт **1/1**; comparison **10/10**; project authorization **9/9**.

## Предыдущий stable-релиз v225.10

- завершён Stage 5.1 Field Calibration & Report Authorization Integration;
- добавлен project-owned synthetic field-surrogate calibration dataset для 10 методов;
- calibration gate: **10/10**, final-report authorized: **9/10**;
- добавлены RMSE/MAE/bias, sensitivity и uncertainty envelopes;
- final export выполняет authorization до PresentationModel и renderer;
- Professional Print Center показывает read-only diagnostics на русском, казахском и английском;
- foundation Dual Water остаётся `blocked_final_report`;
- запуск: `python scripts/run_petrophysical_stage_5_1_gate.py`;
- [инструкция](docs/user/ru/field_calibration_and_report_authorization.md) · [архитектура](docs/developer/ru/field_calibration_authorization_architecture.md).

- Итоговая проверка v225.10: **2896 passed, 0 failed**; Live Workbench Acceptance: **14/14**; numerical validation: **10/10**; field calibration: **10/10**; final-report authorization: **9/10**.

## Предыдущий stable-релиз v225.9

- завершён Stage 5 Petrophysical Engine Validation Foundation;
- зарегистрированы 10 петрофизических методов с provenance, units, applicability, limitations и report policy;
- добавлены 10 synthetic reference cases, numerical tolerances и uncertainty metadata;
- application-service gate выполняет production-функции и формирует JSON evidence;
- 10/10 методов численно воспроизводимы, 9 разрешены для финального отчёта;
- foundation Dual Water остаётся `blocked_final_report`;
- запуск: `python scripts/run_petrophysical_validation_gate.py`;
- [инструкция](docs/user/ru/petrophysical_validation_gate.md) · [архитектура](docs/developer/ru/petrophysical_validation_architecture.md).
- A3 landscape графики и текстовые разделы используют полную полезную ширину/высоту страницы;
- PDF/DOCX/HTML переведены с фиксированных ширин на `available-frame`;
- [адаптивный макет](docs/user/ru/adaptive_report_layout.md) · [архитектура layout](docs/developer/ru/adaptive_report_layout_architecture.md).
- итоговая проверка v225.9: **2881 passed, 0 failed**; Live Workbench: **14/14**; petrophysical gate: **10/10**.

## Предыдущий stable-релиз v225.8

- Stage 4 переведён в канал **stable**;
- Live Workbench Acceptance проверяет реальный server health и исполняемую Streamlit-сессию;
- build/source identity и пять областей Workbench подтверждены;
- LAS command и LAS Workspace проходят без traceback;
- результат stable promotion: **14/14 passed**;
- полный regression suite: **2858 passed, 0 failed**;
- запуск проверки: `.\run_app.ps1 -ForceRestart -Acceptance`;
- [инструкция](docs/user/ru/stable_release_and_acceptance.md) · [архитектура](docs/developer/ru/live_workbench_acceptance_architecture.md).

## Установка и запуск

Требуется Python 3.10+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\run_app.ps1
```

## Автор

**Сармулдин Р. Р.** — инженер-программист, автор GAS RATIO PRO.
