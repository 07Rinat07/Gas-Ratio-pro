# GAS RATIO PRO

**GAS RATIO PRO** — профессиональная инженерная платформа для обработки, анализа, интерпретации и визуализации геолого-геофизических данных скважин.

Программа предназначена для работы с каротажными данными, LAS-файлами, кривыми ГИС, данными скважин, инженерными расчетами, корреляцией, геологическим моделированием, визуализацией и подготовкой отчетов.

Проект разрабатывается как модульное программное обеспечение для нефтегазовых, геологических, геофизических и петрофизических задач. Основная идея проекта — объединить в одном рабочем пространстве инструменты для загрузки, проверки, редактирования, анализа, интерпретации и экспорта данных скважин.

## Основные возможности

- просмотр и анализ LAS-файлов;
- создание и редактирование LAS-файлов;
- управление каротажными кривыми;
- редактирование заголовков и табличных данных LAS;
- работа с проектами и скважинами;
- визуализация геофизических данных;
- корреляция скважин;
- базовое геологическое моделирование;
- расчетные и статистические инструменты;
- импорт и экспорт инженерных данных;
- подготовка отчетов.

## Системные требования

- Python 3.10 или выше;
- Windows 10/11, Linux или macOS;
- рекомендуется 8 ГБ оперативной памяти и выше.

## Установка

Распакуйте архив проекта или клонируйте репозиторий, затем откройте терминал в папке проекта.

Создайте виртуальное окружение:

```bash
python -m venv .venv
```

Активируйте окружение.

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
source .venv/bin/activate
```

Установите зависимости:

```bash
pip install -r requirements.txt
```

## Запуск проекта

Запуск через Streamlit:

```bash
streamlit run app/streamlit_app.py
```

или:

```bash
python -m streamlit run app/streamlit_app.py
```

После запуска откройте в браузере адрес, который покажет Streamlit. Обычно это:

```text
http://localhost:8501
```

На Windows также можно использовать файл:

```powershell
.\run_app.ps1
```

## Автор проекта

**Сармулдин Р. Р.**

Инженер-программист, автор и разработчик программного комплекса **GAS RATIO PRO**.

## Статус проекта

Проект находится в активной стадии разработки.

## Лицензия

Частный проект. Все права защищены.


## Hydrocarbon Interpretation Engine v1.0

Status: frozen public API after Validation Dataset v2 passes. Next major module: Professional Reporting System.
## Professional Reporting System

The first Professional Reporting System increment adds an Executive Summary layer.
Reports should answer engineering questions first: what intervals were found, where they are located, how reliable they are and what should be checked next. Technical row counters, raw diagnostics and full calculation dumps belong to technical appendices, not to the first report header.

