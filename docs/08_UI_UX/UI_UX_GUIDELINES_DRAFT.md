# UI/UX Guidelines — Draft

## 1. Core UI Rules

- Sidebar is the primary navigation mechanism.
- Dashboard is an engineer workspace, not a navigation duplicate.
- No duplicated central navigation cards.
- Avoid horizontal scrolling.
- Long text must wrap inside cards/tables.
- Keep working panels readable above branded background.

## 2. Workspace Rules

Every professional module should provide:

- Summary header.
- Object table.
- Detail editor.
- Validation area.
- Export/download area.
- History/provenance if applicable.

## 3. LAS Editor UI Requirements

- Creation wizard.
- Header editor tabs.
- Curve manager table.
- ASCII editor table.
- Validation report panel.
- Safe export panel.

## 4. Geological Modeling UI Requirements

- Model object tree.
- Zone/property tables.
- Parameter panels.
- Statistics panels.
- Preview panels.
- Validation messages.

## 5. Interaction Rules

- Destructive actions require confirmation.
- Source LAS overwrite must be blocked.
- Long operations must show progress or diagnostics.
- Errors must explain what happened and how to fix it.

---

# UI/UX v4.0 Addendum — LAS Editor and Correlation Visibility

## LAS Workspace Visibility

LAS Workspace must never show an empty or useless screen. Even without an opened LAS file, it must show primary actions:

- Создать LAS;
- Открыть LAS;
- Импорт LAS/CSV/XLSX;
- Срастить LAS;
- Вставить данные из другого LAS;
- Исправить глубину LAS;
- Шаблоны;
- Последние файлы.

Tools must be grouped into visible expandable panels, not hidden behind unclear tabs.

## Correlation Workspace Clarity

Correlation Workspace must use a clear layout:

- left panel: well selection;
- top toolbar: curves, markers, depth range, scale;
- center: synchronized tracks;
- right inspector: selected well/marker/tie line details;
- bottom panel: validation messages and correlation log.

Empty-state message:

`Выберите минимум две скважины и назначьте LAS-файлы для построения корреляции.`
