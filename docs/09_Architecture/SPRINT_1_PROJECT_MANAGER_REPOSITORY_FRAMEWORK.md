# Sprint 1 — Project Manager & Repository Framework

## Цель

Завершить фундаментальный слой управления проектами, скважинами, LAS-файлами и экспортами без прямого удаления данных из UI.

## Выполнено в этом инкременте

- Добавлен `services/ProjectManagerService`.
- Добавлен `services/WellManagerService`.
- Добавлен `services/LasManagerService`.
- Добавлен `services/ExportManagerService`.
- Добавлен единый `widgets/common/table_toolbar.py`.
- Project selector переведен на `ApplicationStateController` и `ProjectManagerService`.
- Панель сохраненных скважин переведена на `WellManagerService`.
- Панель сохраненных экспортов переведена на `ExportManagerService`.
- Панель LAS-файлов проекта переведена на `LasManagerService`.
- Добавлено физическое удаление экспортов проекта.
- Добавлена очистка всех экспортов проекта.
- Добавлена очистка всех LAS-файлов проекта.
- Удаление последней версии скважины удаляет саму скважину из persistent storage.

## Архитектурное правило

UI не должен напрямую удалять файлы или вызывать низкоуровневые repository-функции для Project/Well/LAS/Export. UI вызывает сервисный слой, сервисный слой вызывает repository/storage.

## Следующий шаг Sprint 1

Продолжить вынос оставшихся прямых `st.session_state` и `st.rerun()` из Project Manager/Repository UI в единый runtime/state слой.
