# Правила ведения документации

Документация является частью продукта. Любое изменение, которое влияет на запуск,
данные, расчеты, интерфейс, логи или интерпретацию, должно сопровождаться
обновлением соответствующего `.md` файла.

## Что обновлять

| Изменение | Документация |
| --- | --- |
| Новая зависимость | `requirements.txt`, `docs/setup.md`, `README.md` при необходимости |
| Новый формат файла | `README.md`, `docs/data_format.md`, `docs/user_guide.md` |
| Новый алиас кривой | `docs/data_format.md`, тест mapping |
| Изменение формулы | `docs/formulas.md`, тест расчетов, `CHANGELOG.md` |
| Изменение интерфейса | `docs/user_guide.md`, `README.md` при необходимости |
| Новый тип экспорта | `docs/user_guide.md`, `README.md` |
| Изменение палеток | `config/palettes.json`, `docs/palettes.md`, `CHANGELOG.md` |
| Изменение логирования | `docs/logging.md`, `docs/troubleshooting.md`, тесты логгера |
| Новая справочная подсказка | `docs/user_guide.md`, тест правила или UI-smoke |
| Исправление важной ошибки | `CHANGELOG.md`, troubleshooting при необходимости |

## Минимальная проверка документации

Перед commit ответьте на вопросы:

- Новый человек сможет установить проект по `README.md`?
- Есть команда запуска?
- Есть команда тестов?
- Понятно, какие форматы данных поддерживаются?
- Понятно, где смотреть `logs/app.log` при ошибке?
- Понятно, какие ограничения у текущей версии?
- Если изменилась формула, обновлен ли `docs/formulas.md`?
- Если изменилась фича, есть ли тест и запись в `CHANGELOG.md`?

## Стиль

- Пишите короткими практическими разделами.
- Добавляйте команды, которые можно выполнить без догадок.
- Не прячьте ограничения и инженерные допущения.
- Не обещайте точность интерпретации без подтвержденной методики.
- Для спорных формул явно пишите статус подтверждения.
- Для логов объясняйте, какие данные туда не должны попадать.

## Обязательное правило

Если пользователь или разработчик задает вопрос "как запустить", "как пользоваться",
"какой формат данных нужен", "где смотреть ошибку" или "почему расчет такой",
ответ должен находиться в документации проекта, а не только в переписке.

## Repository root documentation policy

The repository root must stay clean and contain only files required to run, test, identify, or configure the project.

Allowed documentation file in the root:

- `README.md`

Project documentation, roadmap notes, changelog files, implementation notes, and technical specifications must be stored under `docs/`.

Disallowed in the root:

- `CHANGELOG.md`
- `.aider.chat.history.md`
- `.aider.input.history`
- `*_SUMMARY.md`
- `*_SUMMARY.txt`
- `*_UPDATE_*.md`
- `PROJECT_CONTINUATION_GUIDE*.txt`
- temporary AI-generated notes

The root must not contain assistant, Aider, or other AI-session history files.

## Roadmap v5 documentation rule

All roadmap, architecture, UI/UX and implementation planning documents must be stored under `docs/`. Root-level temporary implementation summaries, AI history files and intermediate reports are not allowed.


## Active documentation hierarchy

The active development sequence is defined only by `docs/PROJECT_ROADMAP.md`.
The factual current state and next permitted increment are defined by `docs/PROJECT_STATUS.md`.
`docs/project_plan.md` and `docs/PROJECT_PROGRESS_NEXT_STEP.md` are compatibility entry points only.

Version-specific implementation notes must be recorded in `docs/CHANGELOG.md`. A new `*_VNNN.md` file is not created unless it documents a stable public contract that cannot be represented in an existing specification.

Replaced plans and historical release notes must be moved under `docs/archive/` and must be clearly treated as non-controlling history.
