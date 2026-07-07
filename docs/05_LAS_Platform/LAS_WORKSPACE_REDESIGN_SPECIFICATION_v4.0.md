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
