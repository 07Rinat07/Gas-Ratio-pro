# GAS RATIO PRO — MASTER PROJECT SPECIFICATION v3.0

**Статус:** обновленная мастер-спецификация после Engineering Review  
**Заменяет:** MASTER_PROJECT_SPECIFICATION_v2.0 как основной источник требований  

---

## 1. Новая цель проекта

GAS RATIO PRO — профессиональная инженерная платформа для создания, редактирования, анализа, интерпретации, визуализации и отчетности по геолого-геофизическим данным скважин.

Главная цель v3.0: превратить набор реализованных foundation-модулей в удобное рабочее приложение, где пользователь видит инструменты, понимает последовательность работы и может получать результаты в профессиональных форматах: PDF, Excel, Word, PNG/SVG/TIFF и LAS.

---

## 2. Главный принцип v3.0

Функция считается реализованной только если выполнены все условия:

1. Есть backend/API.
2. Есть понятный UI-доступ.
3. Есть empty-state, если данные еще не загружены.
4. Есть preview результата.
5. Есть export/print, если результат нужен пользователю.
6. Есть validation/errors.
7. Есть тесты.
8. Есть документация.

Backend-only foundation больше не считается полноценной готовностью пользовательской функции.

---

## 3. Критические требования пользователя

### 3.1 Создание LAS

Пользователь должен иметь возможность создать LAS-файл сразу после входа в LAS Workspace, даже если файл еще не загружен.

Обязательные UI-действия:

- Создать LAS;
- Открыть LAS;
- Импорт из CSV/Excel;
- Шаблоны;
- Последние файлы.

### 3.2 Профессиональные графики

Графики должны поддерживать:

- ручной ввод масштаба X;
- ручной ввод диапазона глубин;
- zoom/pan мышью;
- crosshair;
- маркеры флюидов и контактов;
- печать выбранных интервалов;
- экспорт PDF/PNG/SVG/TIFF.

### 3.3 Отчеты

HTML не является основным форматом отчета.

Основные форматы:

- PDF;
- DOCX;
- XLSX;
- PNG/SVG для графиков;
- Markdown/HTML только как вспомогательные форматы.

### 3.4 Интерпретация всей скважины

Должен быть общий отчет по всей скважине:

- где есть газ;
- где нефть;
- где вода;
- где конденсат;
- где нет признаков коллектора;
- какие интервалы pay/net/gross;
- какие расчеты выполнены;
- какие графики подтверждают вывод.

### 3.5 Геомоделирование

Геомоделирование должно иметь видимые рабочие пространства:

- Structural Modeling;
- Facies Modeling;
- Property Modeling;
- Geostatistics;
- Interpolation;
- Simulation;
- Volumetrics;
- Model Validation.

Пользователь должен видеть, где считать, как считать и где смотреть результат.

---

## 4. Архитектура рабочих пространств

Приложение должно состоять из следующих Workspaces:

1. Dashboard Workspace.
2. Project Workspace.
3. LAS Workspace.
4. Well Workspace.
5. Plot Studio Workspace.
6. Interpretation Workspace.
7. Petrophysical Workspace.
8. Geological Modeling Workspace.
9. Reservoir Workspace.
10. Report Studio Workspace.
11. Data Browser Workspace.
12. Settings Workspace.

Каждый workspace обязан иметь:

- заголовок;
- action toolbar;
- content area;
- inspector/properties panel;
- output/status area;
- empty state;
- help hints.

---

## 5. UI/UX требования

### 5.1 Visual Style

Интерфейс должен быть современным, аккуратным, инженерным, без перегруженных технических страниц.

### 5.2 Action-first UI

Пользователь должен видеть действия:

- создать;
- открыть;
- импортировать;
- проверить;
- рассчитать;
- построить;
- экспортировать;
- напечатать.

### 5.3 Progressive Disclosure

Сложные инструменты должны раскрываться по нажатию кнопки, а не быть разбросанными по странице.

---

## 6. Plot Studio v2 требования

Plot Studio должен стать одним из центральных модулей проекта.

Минимальный обязательный набор:

- multi-track well log plots;
- manual X/Y/depth scales;
- mouse zoom/pan;
- synchronized depth axis;
- curve styling;
- fluid/contact markers;
- interval bands;
- annotation layer;
- print/export engine;
- saved plot templates.

---

## 7. Report Studio 2.0 требования

Report Studio должен поддерживать:

- PDF;
- DOCX;
- XLSX;
- PNG/SVG/TIFF;
- report templates;
- interval reports;
- full-well reports;
- calculation result reports;
- print preview.

---

## 8. Known Broken / Weak Areas

Следующие области имеют высокий приоритет исправления:

1. LAS creation is not visible without loaded file.
2. Plot interpretation graphs are weak and non-informative.
3. No manual scale controls on plots.
4. No mouse zoom/pan on interpretation plots.
5. No depth interval print controls.
6. Not enough fluid/contact markers.
7. No full well interpretation report in PDF/Excel.
8. Triangular diagram is broken/non-functional.
9. Frontend design is weak.
10. Geological modeling backend is not exposed as usable UI.

---

## 9. Deferred Features

Не входят в текущий обязательный план:

- AI Assistant;
- Licensing / Hardware ID;
- Cloud Sync;
- Multi-user collaboration;
- telemetry.

---

## 10. Acceptance Criteria для Roadmap v4.0

Проект может вернуться к расширению новых научных/инженерных алгоритмов только после выполнения:

1. LAS creation visible and usable from empty LAS Workspace.
2. Plot manual scale controls implemented.
3. Plot mouse zoom/pan implemented.
4. PDF/PNG/SVG export implemented for plots.
5. PDF/XLSX report export implemented.
6. Full well interpretation report implemented.
7. Triangular diagram repaired or removed from active UI.
8. Geological Modeling Home UI implemented.
9. Project Explorer/Data Browser implemented.
10. UI visually unified.
