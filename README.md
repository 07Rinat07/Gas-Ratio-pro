# GAS RATIO PRO

**GAS RATIO PRO** — инженерное приложение для работы с каротажными данными и LAS-файлами: импорт, просмотр, редактирование, подготовка кривых, интерпретация, построение графиков, корреляция скважин, геологическое моделирование, отчеты и экспорт результатов.

Проект развивается как профессиональная модульная платформа для нефтегазовых и геолого-геофизических задач. Основной фокус текущей версии — надежная LAS Platform, безопасное редактирование данных без перезаписи исходных файлов, расширяемая архитектура и документация по принципу **Specification First**.

## Автор

**Сармулдин Р. Р.**

## Суть проекта

Цель проекта — создать удобный инженерный инструмент, который объединяет в одном рабочем пространстве:

- работу с LAS-файлами;
- управление проектами и скважинами;
- анализ и подготовку каротажных кривых;
- построение планшетов и графиков;
- корреляцию скважин;
- базовое геологическое моделирование;
- расчетные и статистические инструменты;
- подготовку отчетов и экспорт данных.

Проект не копирует Petrel, Techlog или другие коммерческие системы. Они используются только как источник идей. GAS RATIO PRO строится как собственная открытая и расширяемая инженерная платформа.

## Текущий статус

Проект перешел в **Phase II — Engineering Specification & Architecture**.

Ключевые решения Phase II:

- документация и спецификация идут перед новой разработкой;
- AI Assistant пока не реализуется;
- Licensing / Hardware ID / Activation отложены и могут быть исключены;
- приоритет разработки — LAS Platform Professional;
- исходные LAS-файлы не перезаписываются, новые версии сохраняются как отдельные файлы.

## Реализованные основные подсистемы

- Dashboard / Workspace
- Project Manager
- Well Manager
- LAS Explorer
- LAS Editor Professional Foundation
- LAS Creation Wizard
- Curve Manager Foundation
- Formation Manager
- Plot Studio
- Statistics Center
- Formula Builder
- Interpretation Workspace
- Report Studio
- Correlation Studio
- Geological Modeling Foundation
- Data Quality & Validation Center
- Batch Processing Center
- Template & Workflow Manager
- Plugin SDK Foundation
- Scripting API Foundation
- Performance & Optimization Foundation
- Release Candidate diagnostic tools

## Как запустить проект

### 1. Установить Python

Рекомендуется Python **3.10+** или **3.11+**.

Проверка версии:

```bash
python --version
```

### 2. Распаковать архив проекта

Например:

```bash
unzip gas-ratio-pro-phase2-b2-curve-manager.zip
cd gas-ratio-pro-phase2-b2-curve-manager
```

На Windows можно просто распаковать ZIP через проводник и открыть папку проекта в терминале.

### 3. Создать виртуальное окружение

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 4. Установить зависимости

```bash
pip install -r requirements.txt
```

### 5. Запустить приложение

```bash
streamlit run app/streamlit_app.py
```

После запуска Streamlit покажет локальный адрес, обычно:

```text
http://localhost:8501
```

Откройте этот адрес в браузере.

### Альтернативный запуск на Windows

В проекте есть PowerShell-скрипт:

```powershell
.\run_app.ps1
```

Если запуск скриптов запрещен, используйте команду Streamlit напрямую:

```powershell
streamlit run app/streamlit_app.py
```

## Как проверить проект

### Быстрая проверка синтаксиса

```bash
python -m compileall app core importers las_editor projects visualization
```

### Запуск тестов

```bash
pytest
```

Если в окружении не установлен `streamlit`, часть smoke-тестов интерфейса может быть пропущена или остановлена. Для полной проверки установите зависимости из `requirements.txt`.

## Структура проекта

```text
app/                 Streamlit-интерфейс
core/                ядро, расчеты, диагностика, preflight
importers/           импорт LAS/CSV/Excel
las_editor/          LAS Editor, LAS Creation Wizard, Curve Manager
projects/            проектные подсистемы и хранилища
visualization/       графики и визуализация
docs/                спецификации, Roadmap, планы и документация
tests/               pytest-тесты
examples/            демонстрационные данные
```

## Главные документы Phase II

- `docs/01_Master_Project_Specification/MASTER_PROJECT_SPECIFICATION_v2.0.md`
- `docs/02_Roadmap/ROADMAP_v3.0.md`
- `docs/05_LAS_Platform/LAS_PLATFORM_SPECIFICATION_DRAFT.md`
- `docs/08_Calculation_Engine/CALCULATION_ENGINE_SPECIFICATION_DRAFT.md`
- `docs/13_Testing/TESTING_SPECIFICATION_DRAFT.md`

## Правила разработки

- сначала спецификация, затем код;
- каждый новый модуль сопровождается тестами;
- нельзя ломать существующий интерфейс;
- нельзя перезаписывать исходные LAS-файлы;
- Dashboard остается рабочим пространством инженера, а не страницей навигации;
- Sidebar остается основной навигацией;
- при регрессии сначала исправляется регрессия, затем продолжается разработка.

## Лицензирование

Модуль Licensing / Hardware ID / Activation пока не реализуется. Его внедрение отложено на самый поздний этап или может быть исключено из текущей версии проекта.
