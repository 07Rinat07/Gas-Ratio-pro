# Архитектура и разработка

## Структура проекта

```text
app/
  streamlit_app.py        Streamlit UI
core/
  calculations.py         Расчетное ядро
  interpretation.py       Правила предварительной классификации
  models.py               Dataclass-модели и стандартные поля
importers/
  csv_importer.py         Чтение CSV
  excel_importer.py       Чтение XLSX/XLSM
  header_detector.py      Поиск и применение строки заголовков
mapping/
  curve_aliases.py        Алиасы кривых
  mapper.py               Авто/manual mapping
palettes/
  config.py               Настройки палеток
  pixler.py               Pixler palette
  ternary.py              Ternary palette
  depth_tracks.py         Графики по глубине
reports/
  export_csv.py           CSV export
  export_xlsx.py          XLSX export helper
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

## Локальная разработка

```powershell
cd C:\OSPanel\home\gas-ratio-pro
.\.venv\Scripts\Activate.ps1
python -m pytest
streamlit run app/streamlit_app.py
```

## Перед commit

Минимальная проверка:

```powershell
python -m pytest
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

Если меняется UI, нужно:

- обновить `docs/user_guide.md`;
- проверить запуск Streamlit вручную.

## Версионирование

Текущая версия: `v0.3`.

Следующие крупные направления:

- v0.4: инженерные палетки и подтвержденные границы зон;
- v0.5: отчеты PDF/PNG/SVG и печатные планшеты;
- v0.6: LAS importer;
- v0.7: структура проектов;
- v1.0: коммерческая MVP.
