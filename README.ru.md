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

## Проверка печати и экспорта v225.6

- добавлены утверждённые golden-artifacts для всех A4/A3 portrait/landscape профилей;
- manifest фиксирует каждую SVG/PNG-страницу, многостраничный PDF, track partition, physical bounds и контрольные суммы;
- end-to-end acceptance-тест проходит путь от сохранения пользовательского профиля до HTML/PDF/DOCX и SVG/PNG delivery;
- PDF preview теперь автоматически вписывается в фактический фрейм отчёта при смешанной ориентации;
- 51 legacy regression contract системно классифицирован, без скрытого `xfail`;
- [инструкция пользователя](docs/user/ru/print_center_page_aware.md);
- [архитектура для разработчика](docs/developer/ru/page_aware_print_architecture.md).

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
