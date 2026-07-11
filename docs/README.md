# GAS RATIO PRO — Documentation Map

Этот файл является единой точкой входа в документацию проекта.

## 1. Управляющие документы

Читать в указанном порядке:

1. [`PROJECT_ROADMAP.md`](PROJECT_ROADMAP.md) — единственная активная последовательность разработки.
2. [`PROJECT_STATUS.md`](PROJECT_STATUS.md) — фактическое состояние проекта и ближайший разрешённый шаг.
3. [`01_Master_Project_Specification/MASTER_PROJECT_SPECIFICATION_v2.0.md`](01_Master_Project_Specification/MASTER_PROJECT_SPECIFICATION_v2.0.md) — требования и границы продукта.
4. [`04_Software_Architecture/SAD_DRAFT.md`](04_Software_Architecture/SAD_DRAFT.md) — архитектурные слои и зависимости.
5. [`00_Project_Charter/PROJECT_DESIGN_PRINCIPLES.md`](00_Project_Charter/PROJECT_DESIGN_PRINCIPLES.md) — обязательные инженерные принципы.

При конфликте документов приоритет такой:

```text
Master Specification
→ Project Roadmap
→ Project Status
→ Architecture / module specifications
→ User and developer guides
→ Changelog and archived notes
```

## 2. Рабочая документация

- [`user_guide.md`](user_guide.md) — руководство пользователя.
- [`development.md`](development.md) — разработка, тестирование и commit workflow.
- [`setup.md`](setup.md) — установка и запуск.
- [`troubleshooting.md`](troubleshooting.md) — диагностика ошибок.
- [`data_format.md`](data_format.md) — форматы данных.
- [`formulas.md`](formulas.md) — формулы и инженерные допущения.
- [`CHANGELOG.md`](CHANGELOG.md) — история изменений.

## 3. Спецификации подсистем

Структурированные каталоги `00_...`–`16_...` содержат спецификации отдельных подсистем. Они описывают требования и архитектуру, но не определяют очередность работ. Очередность определяется только `PROJECT_ROADMAP.md`.

## 4. Архив

- `archive/releases/` — исторические заметки конкретных версий.
- `archive/legacy_plans/` — старые планы, freeze-документы и прежние progress-файлы.

Архивные документы не являются активными требованиями и не должны использоваться для выбора следующей задачи.

## 5. Правило обновления

После каждого инкремента обновляются только:

- `PROJECT_STATUS.md` — фактический статус и следующий шаг;
- `CHANGELOG.md` — что изменено;
- соответствующая стабильная спецификация, если изменился контракт.

Новый отдельный файл вида `*_V175.md` создавать запрещено без отдельного архитектурного обоснования.
