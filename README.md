# Gas Ratio Interpreter v0.3

Локальное инженерное приложение для импорта газовых данных, сопоставления колонок,
расчета газовых коэффициентов, построения Pixler/ternary палеток и предварительной
интерпретации интервалов.

Документация ведется так, чтобы новый пользователь мог развернуть проект с нуля,
запустить интерфейс, загрузить файл и проверить расчет без знания внутреннего кода.

## Быстрый старт

Требования:

- Windows 10/11, Linux или macOS
- Python 3.11+
- Git

Команды для Windows PowerShell:

```powershell
git clone <repo-url> gas-ratio-pro
cd gas-ratio-pro
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest
python scripts/preflight.py
python -m streamlit run app/streamlit_app.py
```

После запуска Streamlit откроет локальный адрес вида:

```text
http://localhost:8501
```

Если проект уже находится на компьютере:

```powershell
cd C:\OSPanel\home\gas-ratio-pro
.\.venv\Scripts\Activate.ps1
python -m streamlit run app/streamlit_app.py
```

## Как проверить без рабочих данных

В проекте есть тестовый файл:

```text
examples/sample_gas_data.csv
examples/sample_gas_data.las
```

Запустите приложение, загрузите LAS или CSV и оставьте автоматически найденную
строку заголовков. В интерфейсе должны появиться таблица расчетов, сводка
классификации, Pixler/ternary палетки и графики по глубине.

## Что умеет v0.3

- Импорт LAS, CSV, XLSX, XLSM.
- LAS-редактор: проверка глубины, исправление убывающего порядка глубины, изменение шага, добавление строк, ручная правка и передача подготовленных данных в расчеты.
- Локальное хранение скважин в `data/wells/` с версиями и выгрузкой `CSV`, `XLSX`, `LAS`.
- Чтение всех листов Excel.
- Автоматический поиск строки заголовков среди первых 50 строк.
- Ручной выбор строки заголовков.
- Автоматическое и ручное сопоставление колонок.
- Поддержка разных названий кривых: `Depth`, `DEPT`, `MD`, `CH4`, `Methane`,
  `i-C4`, `n-C4`, русские названия и другие алиасы.
- Расчет `Wh`, `Bh`, `BAR2`, Pixler ratios, ternary ratios и настраиваемого `Ch`.
- Предварительная инженерная классификация интервалов.
- Pixler palette, ternary palette и depth tracks.
- Настройка Pixler/ternary палеток через `config/palettes.json`.
- Локальное диагностическое логирование в `logs/app.log`.
- Локальный ИИ-помощник по документации в offline-first режиме.
- Каталог профилей локальных AI-моделей для подготовки работы без интернета.
- Manifest локальной RAG-базы знаний для проверяемых ответов AI-помощника.
- Проверяемые Q/A-примеры для частых вопросов AI-помощника.
- Локальная AI evaluation-команда для проверки RAG и safety-контракта.
- Экспорт расчетной таблицы в CSV.
- Pytest-набор для проверки расчетов, mapping, импорта, примера данных, палеток и логирования.

## Важные ограничения

- Интерпретация является предварительной инженерной подсказкой.
- Результат требует проверки по ГИС, литологии, буровому контексту, фону,
  СПО, наращиваниям и рециркуляции.
- Формула `Ch` требует подтверждения по корпоративной методике.
- Границы зон Pixler/ternary в текущем конфиге являются черновыми и должны быть
  заменены на подтвержденные корпоративные линии.
- PDF/PNG/SVG отчеты, расширенная RAG/AI-база знаний и полноценная база проектов планируются в следующих версиях.

## Карта документации

- [Установка и запуск](docs/setup.md)
- [Руководство пользователя](docs/user_guide.md)
- [Формат входных данных](docs/data_format.md)
- [План LAS-редактора](docs/las_editor_plan.md)
- [Формулы](docs/formulas.md)
- [Конфигурация палеток](docs/palettes.md)
- [Логирование](docs/logging.md)
- [Локальный ИИ-помощник](docs/ai_usage.md)
- [Локальная база знаний AI-помощника](docs/knowledge_base.md)
- [Локальный AI-агент](docs/local_ai_agent.md)
- [AI training pack](docs/ai_training_pack.md)
- [Проверка качества AI-помощника](docs/ai_evaluation.md)
- [Профили локальных AI-моделей](docs/local_model_profiles.md)
- [План локального ИИ-помощника](docs/ai_agent_plan.md)
- [Архитектура и разработка](docs/development.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Правила ведения документации](docs/documentation_policy.md)
- [История изменений](CHANGELOG.md)

## Основные команды

```powershell
# Запуск тестов
python -m pytest

# Проверка готовности окружения
python scripts/preflight.py

# Просмотр профилей локальных AI-моделей
python scripts/ai_models.py

# Просмотр/настройка AI-provider
python scripts/ai_config.py status

# План подготовки локального AI-агента
python scripts/setup_local_agent.py --profile balanced

# Проверка локальной базы знаний AI-помощника
python scripts/knowledge_base.py

# Проверка качества AI-помощника
python scripts/evaluate_ai.py
python scripts/evaluate_ai.py --provider-mode configured

# Экспорт безопасного AI training/evaluation pack
python scripts/export_ai_training_pack.py

# Запуск приложения
python -m streamlit run app/streamlit_app.py

# Просмотр последних строк лога
Get-Content logs/app.log -Tail 80

# Проверка текущего git-состояния
git status --short
```
