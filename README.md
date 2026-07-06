# Gas Ratio Pro

Gas Ratio Pro — локальное инженерное приложение для работы с LAS/CSV/Excel, газовым каротажем, проектными скважинами, расчетами, LAS-корреляцией, интерпретационными графиками и отчетами.

## Быстрый старт

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

Локальный адрес Streamlit обычно выглядит так:

```text
http://localhost:8501
```

## Основные возможности

- Импорт LAS, CSV, XLSX/XLSM.
- Автоматическое определение строки заголовков и mapping колонок.
- Расчет газовых коэффициентов и предварительная интерпретация интервалов.
- LAS Editor: depth grid, ручная правка, rename/alias/merge кривых, grouping, categories, units, metadata, duplicate detection и quality flags.
- LAS-корреляция нескольких скважин.
- Project Explorer, Well Manager, Dataset Manager и Project Database.
- Экспорт CSV, HTML, XLSX, LAS и статических графиков.
- Современный Dashboard с адаптивной версткой и фирменным оформлением.

## Проверка проекта

```powershell
python -m pytest
python scripts/preflight.py
```

Если `preflight` сообщает об отсутствии зависимостей, установите их через:

```powershell
pip install -r requirements.txt
```

Для PNG/PDF/SVG экспорта требуется `kaleido`.

## Примеры данных

```text
examples/sample_gas_data.csv
examples/sample_gas_data.las
```

Их можно использовать для проверки импорта, mapping, расчетов, LAS Editor и графиков без рабочих данных.

## Документация

- `docs/project_plan.md` — дорожная карта проекта.
- `docs/user_guide.md` — руководство пользователя.
- `docs/las_editor_plan.md` — план и описание LAS Editor.
- `docs/setup.md` — установка и запуск.
- `docs/troubleshooting.md` — частые проблемы.
- `docs/development.md` — архитектура и разработка.

## Лицензия

Проект распространяется по proprietary-лицензии. Исходный код, ресурсы, документация и связанные материалы принадлежат Rinat Sarmuldin. Коммерческое использование, распространение, модификация, production/SaaS/internal company use допускаются только с предварительного письменного разрешения автора.

Полный текст лицензии находится в `LICENSE`.
