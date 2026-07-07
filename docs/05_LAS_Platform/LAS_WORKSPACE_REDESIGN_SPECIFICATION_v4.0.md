# GAS RATIO PRO — LAS WORKSPACE REDESIGN SPECIFICATION v4.0

## 1. Главная проблема

Функция создания LAS реализована, но пользователь ее не видит, если файл не загружен. Это нарушает базовую UX-логику.

---

## 2. Новый стартовый экран LAS Workspace

При входе в LAS Workspace всегда показывать:

- Создать LAS;
- Открыть LAS;
- Импорт CSV/Excel;
- Шаблоны LAS;
- Последние файлы;
- Открыть пример.

---

## 3. LAS Creation Wizard

Шаги:

1. Общая информация по скважине.
2. Диапазон глубин.
3. Шаг.
4. Null value.
5. Выбор шаблона кривых.
6. Preview.
7. Safe export.

---

## 4. Инструменты после открытия/создания файла

- Header Editor;
- Curve Manager;
- ASCII Editor;
- Validator;
- Quality Control;
- Curve Calculator;
- Processing Pipeline;
- Safe Export;
- Report.

---

## 5. Acceptance Criteria

1. Создать LAS можно без загруженного файла.
2. Кнопка создания видна сразу.
3. Мастер создания понятен.
4. Export не перезаписывает исходный файл.
5. Созданный LAS можно сразу открыть в Plot Studio.

---

## 6. Data Cleanup & Session State Manager

При смене активного проекта, скважины или LAS-файла приложение обязано очистить все временные данные рабочей сессии:

- графики и настройки текущего просмотра;
- результаты расчетов;
- интерпретации;
- диагностические таблицы;
- маркеры;
- временные ASCII/Curve/Validator буферы;
- preview-данные.

Глобальные пользовательские настройки не удаляются: тема, язык, лицензия, EULA, workspace settings.

Реализация: `core.session_state_manager`.

Acceptance Criteria:

1. При смене проекта очищаются временные LAS/plot/calculation/interpretation данные.
2. При смене скважины очищаются временные данные предыдущей скважины.
3. При смене LAS очищаются таблицы, графики, валидатор, pipeline preview и маркеры предыдущего файла.
4. Глобальные настройки пользователя сохраняются.
5. Результат очистки возвращает manifest для Operation Journal.

---

## 7. Depth Repair Center

Если глубина убывает, система выполняет ремонт только на рабочей копии таблицы. Оригинальный LAS не перезаписывается.

Правило ремонта:

- определяется depth curve: `DEPT`, `DEPTH`, `MD`, `TVD`;
- если глубина убывает, строки сортируются стабильной сортировкой по глубине;
- газ, GR, RHOB и остальные кривые перемещаются вместе со своей исходной строкой глубины;
- значения кривых не сортируются отдельно и не интерполируются в этом режиме;
- дубликаты глубин сохраняют относительный порядок;
- null/non-numeric depth считаются небезопасным состоянием и блокируют автоматический ремонт при `fail_on_errors=True`.

Реализация: `las_editor.depth_repair`.

Acceptance Criteria:

1. Исходный DataFrame/LAS не мутируется.
2. При убывающей глубине создается исправленная рабочая копия.
3. Все измерения остаются привязанными к исходным depth rows.
4. Операция формирует history и manifest для Operation Journal.
5. Дубликаты и null depth диагностируются отдельно.


---

## 8. Diagnostics Center

Diagnostics Center является read-only orchestration layer для LAS Workspace. Он собирает результаты проверок из Validator, Quality Control и Depth Repair Center в единый отчет для UI, экспорта и Operation Journal.

Назначение:

- показать пользователю все проблемы LAS в одном месте;
- разделить источник проблемы: validator, quality_control, depth_repair;
- не выполнять исправления автоматически;
- не изменять исходный LAS/DataFrame;
- направлять пользователя в специализированный workspace для исправления.

Реализация: `las_editor.las_diagnostics_center`.

Входные данные:

- ASCII DataFrame рабочей копии LAS;
- header cards при наличии;
- sections или raw LAS text при наличии;
- depth curve, expected step, null value;
- optional quality profiles и units.

Выходные данные:

- `LasDiagnosticsReport`;
- нормализованный список `LasDiagnosticFinding`;
- summary по severity, source и code;
- manifest для Operation Journal;
- Markdown-отчет;
- UI-ready table rows.

Acceptance Criteria:

1. Diagnostics Center работает только в read-only mode.
2. Исходный DataFrame/LAS не мутируется.
3. Validator findings, Quality Control issues и Depth Repair issues приводятся к единому формату.
4. Для каждой проблемы сохраняется source, severity, code, message, curve/section/row и recommendation.
5. Report содержит status: `passed`, `warning` или `failed`.
6. Manifest пригоден для Operation Journal и последующего экспорта.
7. Исправления выполняются только в соответствующих специализированных центрах, а не внутри Diagnostics Center.
