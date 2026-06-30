# Архитектура и разработка

## Структура проекта

```text
ai/
  assistant.py            Сбор контекста и вызов provider
  config_writer.py        Безопасная запись config/ai.json
  evaluation.py           Локальная проверка качества AI/RAG
  factory.py              Выбор provider по config/ai.json
  knowledge_base.py       Поиск по локальной документации
  knowledge_manifest.py   Загрузка manifest источников RAG
  knowledge_qa.py         Загрузка проверяемых Q/A-примеров
  model_profiles.py       Загрузка и валидация профилей локальных моделей
  ollama_client.py        Локальный Ollama provider
  provider.py             Provider contract
  settings.py             Загрузка config/ai.json
app/
  streamlit_app.py        Streamlit UI
config/
  ai.json                 Конфигурация локального AI-помощника
  ai_eval_cases.json      Кейсы проверки качества AI-помощника
  ai_model_profiles.json  Профили рекомендуемых локальных AI-моделей
  knowledge_qa.json       Проверяемые Q/A-примеры AI-помощника
  knowledge_sources.json  Manifest локальной базы знаний AI-помощника
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
mapping/
  curve_aliases.py        Алиасы кривых
  mapper.py               Авто/manual mapping
palettes/
  config.py               Загрузчик и валидация палеточного конфига
  pixler.py               Pixler palette
  ternary.py              Ternary palette
  depth_tracks.py         Графики по глубине
reports/
  export_csv.py           CSV export
  export_xlsx.py          XLSX export helper
logs/
  app.log                 Локальный runtime-лог, не коммитится
examples/
  sample_gas_data.csv     Демо-файл для проверки приложения
scripts/
  ai_config.py            Просмотр и переключение AI-provider
  ai_models.py            Просмотр профилей локальных AI-моделей
  evaluate_ai.py          Проверка качества AI/RAG
  knowledge_base.py       Проверка manifest и поиска локальной базы знаний
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
- Ошибки workflow должны логироваться в `logs/app.log` без записи сырых таблиц.

## Локальная разработка

```powershell
cd C:\OSPanel\home\gas-ratio-pro
.\.venv\Scripts\Activate.ps1
python -m pytest
python scripts/preflight.py
python scripts/knowledge_base.py
python scripts/evaluate_ai.py
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

Если добавляется AI-функциональность, нужно:

- начинать с provider interface, offline provider и fake provider для тестов;
- не подключать облачные API без явного разрешения;
- не логировать полные пользовательские таблицы и сырые данные;
- обновить `docs/ai_usage.md`, `docs/knowledge_base.md`, `docs/local_model_profiles.md` и `docs/ai_agent_plan.md`;
- покрыть prompt contract, профильные конфиги, Q/A-каталог, evaluation-кейсы и отказоустойчивость тестами.

## Тестовая стратегия

Минимум для каждой фичи:

- unit-тест на расчетную или сервисную логику;
- тест на ошибочный/пустой вход;
- тест на пользовательский пример, если фича влияет на workflow;
- обновление документации, чтобы фичу можно было проверить вручную.

## Версионирование

Текущая версия: `v0.3`.

Следующие крупные направления:

- v0.4: инженерные палетки и подтвержденные границы зон;
- v0.5: отчеты PDF/PNG/SVG и печатные планшеты;
- v0.6: LAS importer;
- v0.7: структура проектов;
- v0.8: локальный ИИ-помощник по документации и интерпретации;
- v1.0: коммерческая MVP.
