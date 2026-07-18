# GAS RATIO PRO

**Пользовательские руководства / Пайдаланушы нұсқаулықтары / User guides:** [Русский](docs/user/ru/index.md) · [Қазақша](docs/user/kk/index.md) · [English](docs/user/en/index.md)

**Описание проекта / Жоба сипаттамасы / Project overview:** [Русский](README.ru.md) · [Қазақша](README.kk.md) · [English](README.en.md)

![Интерфейс инженерной платформы GAS RATIO PRO](assets/branding/GASRATIOpro.png)

**GAS RATIO PRO** — профессиональная трёхъязычная инженерная платформа для импорта, контроля качества, управления версиями, анализа, интерпретации и визуализации скважинных, геолого-геофизических и проектных данных нефтегазовой отрасли.

Платформа уже поддерживает рабочие процессы с **LAS 1.x/2.x/3.x, Excel и CSV**, а также безопасный metadata-only preview для **DLIS, LIS79 и SEG-Y**. Архитектура Data Platform подготовлена для последующего подключения **GeoPackage, Shapefile, GeoTIFF, GRDECL, RESQML, HDF5 и NetCDF** через изолированные адаптеры и открытые отраслевые стандарты.

## Основные возможности

- импорт, просмотр и редактирование LAS, включая архивные LAS старее 2.0;
- импорт Excel/CSV и автоматическое сопоставление инженерных колонок;
- metadata preview для DLIS, LIS79 и SEG-Y без загрузки тяжёлых массивов;
- SEG-Y header scan, trace-header inventory и диагностика геометрии inline/crossline/X/Y;
- единый Format Registry, Import Pipeline, профили импорта и readiness score;
- immutable artifacts, Dataset Manifest, SHA-256, provenance и история версий;
- LAS Quality Control, стабильные QC-коды и отчёты PDF/DOCX;
- расчёт газогеохимических параметров и газовых отношений;
- выделение и интерпретация углеводородных интервалов;
- работа с кривыми ГИС, литологией и непроницаемыми перемычками;
- многоскважинная корреляция и подготовка корреляционных workflow;
- Project Explorer, Workbench, Diagnostics Center и проектная база метаданных SQLite;
- интерфейс и документация на русском, казахском и английском языках;
- развитие в сторону петрофизики, GIS, 3D, геологического и резервуарного моделирования.

## Поддержка форматов

| Формат | Текущий уровень поддержки |
|---|---|
| LAS 1.x / 2.x / 3.x | Импорт, legacy compatibility, редактирование, QC, версии, визуализация и экспорт |
| Excel / CSV | Импорт, mapping, расчёты и визуализация |
| DLIS | Metadata preview через optional adapter, выбор logical file/frame/channel развивается |
| LIS79 | Metadata preview через optional adapter |
| SEG-Y | Header preview, geometry diagnostics и optional trace-header inventory |
| PDF / DOCX | Генерация и регистрация инженерных/QC-отчётов |
| GeoPackage / Shapefile / GeoTIFF | Запланировано в GIS Platform |
| GRDECL / RESQML | Запланировано в Reservoir Platform |
| HDF5 / NetCDF | Запланировано для крупных многомерных данных |

Актуальная матрица возможностей и ограничения описаны в [пользовательской документации](docs/user/ru/supported_formats_and_legal_sources.md).

## Архитектурные принципы

- исходные данные сохраняются неизменяемыми;
- новые форматы подключаются через адаптеры и единый Data Platform contract;
- тяжёлые зависимости загружаются лениво;
- новые функции сразу документируются на `ru / kk / en`;
- сторонний код и спецификации используются только после лицензионной проверки;
- preview и диагностика больших файлов выполняются с ограничением памяти.

## Стабилизация архитектуры и тестов v225.7

- устранены все 9 нарушений architecture boundary: UI больше не удаляет файлы напрямую, cache telemetry создаётся контейнером, lifecycle и rerun проходят через application services;
- 26 хрупких source assertions заменены исполняемыми поведенческими тестами (18 из legacy registry, Print Center contract и 7 PDF preview contracts);
- 13 визуальных контрактов переведены на утверждённый semantic rebaseline с SHA-256 manifest;
- исторические version pins и устаревшие Workbench assertions заменены current-runtime контрактами;
- все 51 унаследованный regression contract закрыты без `xfail` и без удаления nodeid;
- PDF/DOCX используют общий renderer-neutral print-readability contract;
- полный regression suite завершён: **2855 passed, 0 failed**; расширенный release-контур: **480 passed**;
- [инструкция пользователя](docs/user/ru/print_center_page_aware.md);
- [архитектура для разработчика](docs/developer/ru/page_aware_print_architecture.md).

## Установка

Требуется Python 3.10 или выше.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\run_app.ps1
```

Linux / macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
```

После запуска откройте адрес Streamlit, обычно `http://localhost:8501`.

## Статус проекта

Проект находится в активной разработке. Реализованные возможности, ограничения и дальнейшие этапы доступны через языковые индексы пользовательской и developer-документации.

## Автор проекта

**Сармулдин Р. Р.** — инженер-программист, автор и разработчик программного комплекса **GAS RATIO PRO**.

## Лицензия

Частный проект. Все права защищены. Использование сторонних компонентов регулируется [лицензионной политикой проекта](docs/LICENSE_POLICY.md).
