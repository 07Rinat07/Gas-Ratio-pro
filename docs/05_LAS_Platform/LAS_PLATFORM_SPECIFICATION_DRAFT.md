# LAS Platform Specification — Draft

Project: GAS RATIO PRO  
Priority: Highest after Phase II documentation

## 1. Purpose

LAS Platform is the core subsystem for reading, creating, editing, validating, calculating and exporting LAS files.

## 2. Current Gap

The current LAS Editor foundation supports several editing operations. Phase II implementation has now started closing the largest gap: LAS creation from scratch. Full professional editing workflows are still being expanded incrementally.

## 3. Required Modules

### 3.1 LAS Creation Wizard

Status: **Implemented backend foundation in Phase II B.1**.

The wizard must allow creation of a valid LAS file from scratch.

Required inputs:

- LAS version/profile.
- Well name.
- UWI/API.
- Field.
- Company/operator.
- Start depth.
- Stop depth.
- Step.
- Null value.
- Depth unit.
- Default curve set.

Generated sections:

- `~Version`
- `~Well`
- `~Curve`
- `~Parameter`
- `~Other`
- `~Ascii`

### 3.2 Header Editor

Must support editing:

- Version section.
- Well section.
- Curve section.
- Parameter section.
- Other section.

### 3.3 Curve Manager

Must support:

- Add curve.
- Delete curve.
- Rename curve.
- Reorder curve.
- Change unit.
- Change description.
- Assign category.
- Apply alias.
- Validate mnemonic uniqueness.

### 3.4 ASCII Data Editor

Must support:

- View table.
- Edit values.
- Insert row.
- Delete row.
- Insert depth sample.
- Delete depth sample.
- Replace nulls.
- Bulk fill.

### 3.5 LAS Validator

Must check:

- Mandatory sections.
- Required well metadata.
- Curve count vs ASCII columns.
- Depth monotonicity.
- Duplicate depth values.
- Null value consistency.
- Invalid units.
- Empty curve mnemonic.
- Unsafe overwrite attempt.

### 3.6 Safe LAS Writer

Rules:

- Never overwrite source file.
- Always save edited LAS under a new name.
- Write export manifest.
- Attach validation report.

### 3.7 Curve Calculator

Supported operations:

- Arithmetic formulas.
- Conditional formulas.
- Moving average.
- Median filter.
- Despike.
- Smoothing.
- Normalization.
- Gas ratios.

### 3.8 Import External Curves

Supported sources:

- CSV.
- XLSX.

Required behavior:

- Select depth column.
- Select imported curves.
- Match/resample depth.
- Detect conflicts.
- Create new LAS version.

## 4. Acceptance Criteria

The LAS Platform Professional milestone is complete when:

- A user can create a valid LAS from scratch.
- A user can add/edit/delete curves.
- A user can edit header sections.
- A user can edit ASCII values safely.
- A user can validate LAS before export.
- A user can export only to a new LAS file.
- Unit tests cover validator, writer, creation wizard backend and curve operations.


## 5. Phase II B.1 Implementation Notes

Implemented backend capabilities:

- `LasCreationSpec` for wizard input.
- `LasCurveSpec` for curve definition.
- Built-in templates: empty, mud gas and petrophysics.
- Depth grid generation from start/stop/step.
- Mandatory LAS sections: `~Version`, `~Well`, `~Curve`, `~Parameter`, `~ASCII`.
- Safe in-memory LAS text and bytes generation.
- Mnemonic and unit normalization.
- Basic validation issues for depth range, depth step, duplicate curves and required sections.
- Curve add/delete helpers that protect the depth curve from deletion.

Remaining LAS Platform work:

- UI wizard integration.
- Full header editor.
- ASCII table editor.
- Strict LAS profile validation.
- Curve import from CSV/XLSX into created LAS files.
- Formula-based Curve Calculator.
- LAS Quality Control Professional.

## Phase II B.2 — LAS Curve Manager Professional Foundation

Curve Manager является единым слоем управления кривыми LAS-файла. Он не должен напрямую перезаписывать исходный LAS-файл и обязан работать через рабочую копию данных и manifest metadata.

Обязательные функции B.2:

- построение manifest по всем кривым;
- фиксация порядка кривых;
- защита depth/reference-кривых от удаления;
- добавление новой кривой;
- удаление пользовательских и расчетных кривых;
- переупорядочивание кривых;
- alias, group, category, unit, quality, status, description;
- UI-ready таблицы для отображения Curve Manager;
- журнал операций;
- подготовка данных для последующего безопасного LAS export.

Критерии приемки:

- DEPT остается первой кривой после reorder;
- DEPT/DEPTH/MD/TVD не удаляются через Curve Manager;
- metadata-only операции не изменяют числовые значения кривых;
- все изменения фиксируются в history;
- тесты Curve Manager проходят без Streamlit.


## Phase II B.3 — LAS Header Editor Professional Foundation

Header Editor отвечает за безопасное редактирование metadata LAS-файла. Он работает с секциями `~Version`, `~Well`, `~Curve` и `~Parameter` как с нормализованными карточками `LasHeaderCard`. Редактирование header не должно изменять значения ASCII-таблицы кривых.

Обязательные функции B.3:

- создание минимального набора header-card для нового LAS;
- manifest по секциям LAS;
- редактирование значения, единицы измерения, описания и порядка;
- добавление пользовательских элементов header;
- удаление только незащищенных элементов;
- защита обязательных элементов `VERS`, `WRAP`, `STRT`, `STOP`, `STEP`, `NULL`, `DEPT`;
- проверка обязательных элементов LAS;
- проверка положительного `STEP`;
- предупреждение при `STRT > STOP`;
- UI-ready таблица header elements;
- render helper для подготовки LAS header text;
- журнал header-only операций.

Критерии приемки:

- обязательные элементы нельзя удалить через Header Editor;
- update header-card не меняет LAS ASCII data;
- invalid STEP возвращает validation issue;
- render содержит секции `~Version`, `~Well`, `~Curve`, `~Parameter`;
- тесты Header Editor проходят без Streamlit.

## B.4 LAS ASCII Data Editor Professional Foundation

Модуль отвечает за безопасное редактирование данных секции `~ASCII` в рабочей копии LAS. Функции: табличное представление данных, редактирование отдельной ячейки, массовое редактирование диапазонов, вставка и удаление строк, сортировка по глубине, поиск и замена значений, проверка пустой ASCII-секции, нечисловых глубин, дубликатов глубины, нарушения шага и NULL-значений. Исходный LAS-файл не перезаписывается.


## B.5 LAS Validator Professional Foundation

LAS Validator является единым backend-компонентом контроля качества LAS workspace перед экспортом. Он объединяет проверки структуры LAS, metadata заголовка, списка кривых и ASCII-таблицы. Компонент не выполняет запись файлов и не изменяет рабочие данные.

Обязательные функции:

- определение присутствующих секций LAS по тексту или workspace manifest;
- проверка обязательных секций;
- проверка header-card элементов `VERS`, `WRAP`, `STRT`, `STOP`, `STEP`, `NULL`, `DEPT`;
- проверка пустых секций заголовка;
- проверка дубликатов header-card;
- сверка `~Curve` и `~ASCII`;
- проверка depth column;
- проверка числового типа глубины;
- проверка дубликатов глубины;
- проверка монотонности и шага;
- проверка соответствия `STRT`/`STOP`;
- подсчет NULL-значений;
- формирование отчета `LasValidationReport`;
- UI-ready таблица findings;
- текстовый markdown-отчет качества.

Критерии приемки:

- валидатор возвращает `passed`, `warning` или `failed`;
- ошибки блокируют безопасный экспорт LAS;
- предупреждения не блокируют экспорт, но должны быть видны пользователю;
- все findings содержат код, сообщение и рекомендацию;
- компонент работает без Streamlit и внешнего UI.

## B.6 LAS Safe Export Professional Foundation

LAS Safe Export — компонент безопасного сохранения новых LAS-файлов. Он закрывает ключевое архитектурное правило проекта: исходные LAS-файлы не должны перезаписываться автоматически.

### Назначение

Компонент применяется после создания, редактирования и валидации LAS workspace. Он формирует manifest экспорта, проверяет путь назначения, блокирует опасные операции и выполняет запись только при безопасном состоянии.

### Основные объекты

- `LasTemplateProfile` — профиль шаблона LAS;
- `LasExportIssue` — ошибка или предупреждение экспорта;
- `LasSafeExportManifest` — итоговый manifest операции экспорта.

### Функции

- получение встроенных шаблонов LAS;
- создание LAS specification из шаблона;
- построение таблицы шаблонов для UI;
- проверка target/source path;
- запрет записи поверх исходного LAS;
- запрет случайной перезаписи существующего файла;
- построение export manifest;
- безопасная запись LAS text;
- безопасная запись LAS document из `LasCreationSpec`.

### Критерии приемки

- экспорт в новый `.las` файл работает;
- исходный LAS не перезаписывается даже при `allow_overwrite=True`;
- существующий target блокируется, если перезапись не разрешена;
- manifest содержит статус, пути, размер, количество строк и кривых;
- компонент не зависит от Streamlit;
- функции покрыты pytest-тестами.

## B.9 LAS Curve Import Professional Foundation

Модуль импорта кривых предназначен для добавления новых каротажных кривых из внешних табличных источников без изменения исходного LAS-файла. Импорт выполняется только в рабочую копию данных, после чего пользователь должен выполнить безопасный экспорт через Safe LAS Writer.

### Назначение

- импорт кривых из CSV;
- импорт кривых из XLSX;
- нормализация названий колонок к LAS-safe мнемоникам;
- сопоставление импортируемой таблицы с глубинной сеткой LAS;
- формирование предварительного плана импорта;
- предотвращение случайной перезаписи существующих кривых;
- подготовка manifest для аудита операции.

### Политики сопоставления по глубине

- `exact` — импорт только при точном совпадении глубины;
- `nearest` — выбор ближайшего значения с учетом optional tolerance;
- `interpolate` — интерполяция значений на глубинную сетку целевого LAS.

### Политики конфликтов имен

- `skip` — существующая кривая не изменяется, импорт пропускается;
- `suffix` — создается новая кривая с безопасным суффиксом;
- `replace` — значение в рабочей копии заменяется, исходный LAS-файл все равно не перезаписывается.

### Критерии приемки

- импорт не изменяет исходный LAS-файл;
- все импортируемые мнемоники нормализуются;
- при конфликте имен применяется выбранная политика;
- результат содержит список импортированных и пропущенных кривых;
- формируется manifest операции;
- есть pytest-покрытие для CSV, интерполяции, конфликтов и ошибок плана.

## B.10 LAS Curve Calculator Professional Foundation

Модуль `las_editor.curve_calculator` добавляет безопасный backend для расчета новых LAS-кривых на основе существующих данных `~ASCII`.

### Назначение

Curve Calculator предназначен для создания расчетных кривых без изменения исходного LAS-файла. Все операции выполняются над рабочей копией таблицы и сопровождаются manifest-объектом, историей и диагностикой.

### Поддерживаемые возможности

- проверка выражения до применения;
- расчет новой кривой по формуле;
- защита от перезаписи существующей кривой без явного `overwrite=True`;
- поддержка арифметики, сравнений и булевой логики;
- поддержка функций `IF`, `ABS`, `SQRT`, `LOG`, `LOG10`, `EXP`, `ROUND`, `MIN`, `MAX`;
- preview расчетной кривой;
- создание `LasCurveSpec` для будущего экспорта в `~Curve`;
- встроенные шаблоны газового и петрофизического анализа.

### Встроенные шаблоны

- `wetness_haworth`: `WH = ((C2 + C3 + C4 + C5) / (C1 + C2 + C3 + C4 + C5)) * 100`;
- `balance_haworth`: `BH = (C1 + C2) / (C3 + C4 + C5)`;
- `character_haworth`: `CH = (C4 + C5) / C3`;
- `pixler_c1_c2`: `C1C2 = C1 / C2`;
- `oil_indicator`: `OI = (C3 + C4 + C5) / C1`;
- `inverse_oil_indicator`: `IOI = C1 / (C3 + C4 + C5)`;
- `net_gross_from_facies`: `NG = IF(FACIES == 0, 1, 0)`;
- `porosity_percent`: `POR_PCT = POR * 100`.

### Ограничения безопасности

- не используется Python `eval`;
- не используется Python `exec`;
- запрещены импорт, атрибутный доступ, индексация, циклы, lambda и произвольные вызовы;
- разрешены только заранее определенные функции и операторы.

### Критерии готовности

- формула с неизвестной кривой возвращает validation issue;
- существующая кривая не перезаписывается без явного разрешения;
- расчет не изменяет исходный DataFrame;
- manifest содержит выражение, выходную кривую, используемые кривые и список issues;
- модуль покрыт regression-тестами.
