# GAS RATIO PRO — UI/UX REDESIGN PLAN v4.0

## 1. Цель

Сделать интерфейс GAS RATIO PRO похожим на профессиональное инженерное приложение, а не на набор технических страниц.

---

## 2. Новый layout приложения

```text
┌──────────────────────────────────────────────────────────────┐
│ Top Bar: Project / Well / Status / Global Actions             │
├──────────────┬────────────────────────────────┬──────────────┤
│ Sidebar      │ Workspace Toolbar / Ribbon      │ Inspector    │
│ Navigation   ├────────────────────────────────┤ Properties   │
│              │ Main Workspace                  │              │
├──────────────┴────────────────────────────────┴──────────────┤
│ Output / Logs / Jobs / Validation                             │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Empty-state правило

Если данных нет, страница не должна быть пустой. Она должна показывать действия.

Пример LAS Workspace без файла:

- Создать LAS;
- Открыть LAS;
- Импорт CSV/Excel;
- Выбрать шаблон;
- Открыть пример.

---

## 4. Кнопки и инструменты

Каждый workspace должен иметь крупные понятные кнопки действия.

Плохой вариант:

- скрытые функции;
- инструменты появляются только после загрузки файла.

Правильный вариант:

- действие видно сразу;
- если действие недоступно, показана причина;
- есть подсказка, что нужно сделать.

---

## 5. Приоритетные UI-задачи

1. LAS Start Screen.
2. Plot Studio Toolbar.
3. Manual Scale Panel.
4. Print/Export Panel.
5. Marker/Annotation Panel.
6. Geological Modeling Home.
7. Project Explorer.
8. Data Browser.
9. Job Manager Panel.
10. Unified visual style.

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
