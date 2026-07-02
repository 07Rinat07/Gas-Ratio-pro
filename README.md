# Gas Ratio Interpreter v0.3

Локальное инженерное приложение для импорта газовых данных, сопоставления колонок,
расчета газовых коэффициентов, построения Pixler/ternary палеток, LAS-корреляции
и предварительной интерпретации интервалов по правилам.


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

В проекте есть тестовые файлы:

```text
examples/sample_gas_data.csv
examples/sample_gas_data.las
```

Запустите приложение, загрузите LAS или CSV и оставьте автоматически найденную
строку заголовков. В интерфейсе должны появиться таблица расчетов, сводка
классификации, Pixler/ternary палетки и графики по глубине.

## Что умеет v0.3

- Импорт LAS, CSV, XLSX, XLSM.
- Мультизагрузка файлов в рабочем workflow с выбором набора данных.
- LAS-корреляция: загрузка нескольких LAS, распознавание ГИС/газовых кривых, сохранение настроек в локальный проект и соседние depth-треки для сравнения скважин.
- LAS-редактор: проверка глубины, исправление убывающего порядка глубины, изменение шага, добавление строк, ручная правка и передача подготовленных данных в расчеты.
- Локальное хранение скважин в `data/wells/` с версиями и выгрузкой `CSV`, `XLSX`, `LAS`.
- Локальное хранение настроек LAS-корреляции в `data/projects/default/correlation_settings.json`.
- Чтение всех листов Excel.
- Автоматический поиск строки заголовков среди первых 50 строк.
- Ручной выбор строки заголовков.
- Автоматическое и ручное сопоставление колонок.
- Поддержка разных названий кривых: `Depth`, `DEPT`, `MD`, `CH4`, `Methane`, `i-C4`, `n-C4`, русские названия и другие алиасы.
- Расчет `Wh`, `Bh`, `BAR2`, Pixler ratios, ternary ratios и настраиваемого `Ch`.
- Предварительная инженерная классификация интервалов по проверяемым правилам.
- Pixler palette, ternary palette и depth tracks.
- Интерпретационные depth-графики с ручным диапазоном глубины, ручным X-масштабом и HTML-выгрузкой для печати.
- Настройка Pixler/ternary палеток через `config/palettes.json`.
- Локальное диагностическое логирование в `logs/app.log`.
- Экспорт расчетной таблицы в CSV.
- Pytest-набор для проверки расчетов, mapping, импорта, LAS, палеток, логирования и Streamlit-smoke.

## Важные ограничения

- Интерпретация является предварительной инженерной подсказкой.
- Результат требует проверки по ГИС, литологии, буровому контексту, фону, СПО, наращиваниям и рециркуляции.
- Формула `Ch` требует подтверждения по корпоративной методике.
- Границы зон Pixler/ternary в текущем конфиге являются черновыми и должны быть заменены на подтвержденные корпоративные линии.
- PDF/PNG/SVG отчеты и полноценная база проектов планируются в следующих версиях.

## Карта документации

- [Установка и запуск](docs/setup.md)
- [План проекта](docs/project_plan.md)
- [Руководство пользователя](docs/user_guide.md)
- [Формат входных данных](docs/data_format.md)
- [План LAS-редактора](docs/las_editor_plan.md)
- [План multi-LAS корреляции](docs/las_correlation_plan.md)
- [Формулы](docs/formulas.md)
- [Mud gas analysis: литературный источник](docs/mud_gas_analysis_literature.md)
- [Конфигурация палеток](docs/palettes.md)
- [Логирование](docs/logging.md)
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

# Запуск приложения
python -m streamlit run app/streamlit_app.py

# Просмотр последних строк лога
Get-Content logs/app.log -Tail 80

# Проверка текущего git-состояния
git status --short
```
