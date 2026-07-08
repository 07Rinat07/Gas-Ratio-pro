# Sprint 1.5 — Platform Health Verification

## Назначение

Этот документ фиксирует первый интеграционный проход Sprint 1.5. Цель прохода — не добавлять новый функционал, а проверить, что ядро платформы после Service Compatibility Pass работает как единая система.

## Добавленные проверки

### 1. Service Contracts

Проверяются публичные контракты основных сервисов:

- `DatasetManagerService`
- `ProjectManagerService`
- `LasManagerService`
- `WellManagerService`
- `ExportManagerService`

Если UI или другой слой ожидает compatibility-метод, он должен существовать до завершения миграции на новую архитектуру.

### 2. Storage Lifecycle Imports

Проверяется доступность ключевых компонентов:

- `ResourceManager`
- `FileHandleManager`
- `CacheManager`
- `DeleteEngine`
- `IndexManager`

### 3. UI Storage Boundary

`app/streamlit_app.py` не должен выполнять прямые разрушительные операции с файловой системой:

- `shutil.rmtree(...)`
- `os.remove(...)`
- `os.rmdir(...)`
- `Path.unlink(...)`
- `Path.rmdir(...)`

Удаление должно проходить через сервисный слой и `DeleteEngine`.

### 4. Storage Directories

Проверяются и создаются при необходимости:

- `data/projects`
- `data/wells`
- `logs`

## Результат

Добавлен модуль:

```text
core/platform_health.py
```

Добавлены regression-тесты:

```text
tests/test_sprint_1_5_platform_health.py
```

Эти проверки становятся частью Sprint 1.5 и должны проходить перед переходом к Sprint 2.
