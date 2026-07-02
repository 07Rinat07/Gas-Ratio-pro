# Архитектура и разработка

## Структура проекта

```text
app/
  streamlit_app.py        Streamlit UI
config/
  palettes.json           Внешняя конфигурация Pixler/ternary палеток
core/
  calculations.py         Расчетное ядро
  interpretation.py       Правила предварительной классификации
  logging_config.py       Настройка локального логирования
  models.py               Dataclass-модели и стандартные поля
importers/
  csv_importer.py         Чтение CSV
  excel_importer.py       Чтение XLSX/XLSM
  header_detector.py      Поиск и применение строки заголовков
  las_importer.py         Чтение LAS-файлов
las_correlation/
  core.py                 Подготовка нескольких LAS и классификация кривых
  charts.py               ГИС/газовые correlation-графики
  settings.py             Настройки LAS-корреляции
  settings_store.py       JSON-хранение настроек корреляции проекта
las_editor/
  depth_grid.py           Проверка глубин, сетка шага и заполнение LAS-строк
mapping/
  curve_aliases.py        Алиасы кривых
  mapper.py               Авто/manual mapping
projects/
  repository.py           Локальные проекты и project.json
palettes/
  config.py               Загрузчик и валидация палеточного конфига
  pixler.py               Pixler palette
  ternary.py              Ternary palette
  depth_tracks.py         Графики по глубине
reports/
  export_csv.py           CSV export
  export_las.py           LAS export helper
  export_xlsx.py          XLSX export helper
wells/
  repository.py           Локальное хранение скважин, manifest и версии данных
logs/
  app.log                 Локальный runtime-лог, не коммитится
data/wells/
  */manifest.json         Локальные скважины и версии данных, не коммитятся
data/projects/
  <project_id>/project.json              Карточка проекта, не коммитится
  <project_id>/correlation_settings.json Настройки LAS-корреляции, не коммитятся
examples/
  sample_gas_data.csv     Демо CSV-файл для проверки приложения
  sample_gas_data.las     Демо LAS-файл для проверки приложения
scripts/
  preflight.py            Проверка окружения перед запуском
tests/
  test_*.py               Pytest-набор
docs/
  *.md                    Документация
```

## Принципы

- Streamlit не должен содержать расчетную бизнес-логику.
- Формулы держим в `core/calculations.py`.
- Интерпретационные правила держим отдельно в `core/interpretation.py`.
- Алиасы кривых добавляем только в `mapping/curve_aliases.py`.
- Импорт не должен зависеть от порядка колонок.
- Деление на 0 должно возвращать `NaN`, а не падение приложения.
- Новые формулы добавляются только после подтверждения источника или методики.
- Границы палеток меняются через `config/palettes.json`, а не через UI-код.
- Новая фича должна иметь тесты, документацию и запись в `CHANGELOG.md`.
- Настройки рабочего workflow сохраняем в файлах проекта, если их потеря после перезапуска мешает пользователю.
- Ошибки workflow должны логироваться в `logs/app.log` без записи сырых таблиц.

## Локальная разработка

```powershell
cd C:\OSPanel\home\gas-ratio-pro
.\.venv\Scripts\Activate.ps1
python -m pytest
python scripts/preflight.py
streamlit run app/streamlit_app.py
```

## Перед commit

Минимальная проверка:

```powershell
python -m pytest
python scripts/preflight.py
git status --short
```

Если меняется логика расчета, нужно:

- добавить или обновить тесты в `tests/test_calculations.py`;
- обновить `docs/formulas.md`;
- отметить изменение в `CHANGELOG.md`.

Если меняется импорт или mapping, нужно:

- добавить тест на новый кейс;
- обновить `docs/data_format.md`;
- при необходимости обновить `mapping/curve_aliases.py`.

Если меняются палетки или их конфиг, нужно:

- обновить `config/palettes.json`;
- обновить `docs/palettes.md`;
- добавить или обновить тесты в `tests/test_palette_config.py`;
- отметить изменение в `CHANGELOG.md`.

Если меняется логирование, нужно:

- обновить `core/logging_config.py` или места вызова логгера;
- добавить или обновить тесты в `tests/test_logging_config.py`;
- обновить `docs/logging.md`;
- убедиться, что сырые данные файлов не попадают в лог.

Если меняется UI, нужно:

- обновить `docs/user_guide.md`;
- проверить запуск Streamlit вручную.

Если добавляется новая справочная логика, она должна быть оформлена как явное
правило, мастер, предупреждение, график, отчет или документация и по возможности
покрыта тестом.
## Тестовая стратегия

Минимум для каждой фичи:

- unit-тест на расчетную или сервисную логику;
- тест на ошибочный/пустой вход;
- тест на пользовательский пример, если фича влияет на workflow;
- обновление документации, чтобы фичу можно было проверить вручную.

## Версионирование

Текущая версия: `v0.3`.

Следующие крупные направления:

- v0.4: LAS-редактор, проверка глубины, изменение шага, заполнение пропусков и хранение скважин;
- v0.5: инженерные палетки и подтвержденные границы зон;
- v0.6: отчеты PDF/PNG/SVG и печатные планшеты;
- v0.7: структура проектов;
- v0.8: мастера диагностики, справочные панели и печатные отчеты;
- v1.0: коммерческая MVP.
