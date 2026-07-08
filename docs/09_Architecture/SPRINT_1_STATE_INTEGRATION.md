# Sprint 1 — Project Manager State Integration

## Цель

Стабилизировать Project Manager после перевода Project/Well/LAS/Export на сервисный слой и убрать прямую запись активного проекта из UI.

## Выполнено

- `_render_project_selector()` переведен на `ApplicationStateController`.
- `_render_recent_projects_manager()` больше не пишет напрямую в `st.session_state[ACTIVE_PROJECT_ID_KEY]`.
- Переключение проекта выполняется через pending activation перед созданием Streamlit widgets.
- Добавлены единые helpers:
  - `_application_state_controller()`;
  - `_refresh_ui()`;
  - `_render_table_toolbar_caption()`.
- Добавлены regression-тесты против возврата прямой записи active project в Project Manager UI.

## Почему это важно

Streamlit запрещает изменять session-state ключ после создания widget с тем же ключом в текущем проходе. Pending activation отделяет состояние приложения от состояния widget и предотвращает `StreamlitAPIException` при создании, открытии и удалении проекта.

## Следующий шаг

Продолжить Integration Pass: пройти остальные repository-панели и убрать оставшиеся ручные refresh/session cleanup участки, которые не относятся к Project Manager.
