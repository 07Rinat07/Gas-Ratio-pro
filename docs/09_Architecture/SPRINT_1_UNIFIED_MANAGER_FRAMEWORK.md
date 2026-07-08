# Sprint 1 — Core Platform & Unified Manager Framework

## Статус текущего инкремента

Добавлены основы Unified Manager Framework:

- `services/dataset_manager_service.py` — сервисный слой Dataset Manager;
- `ui/manager_framework.py` — UI-neutral Toolbar/Table descriptors;
- `services/plugin_manager_service.py` — manifest/hook/registry foundation для Plugin API;
- Dataset Manager в `app/streamlit_app.py` получает единый toolbar для LAS/CSV/Excel/Core/Mud Log/Production секций.

## Dataset Manager 2.0

Каждая секция Dataset Manager должна иметь панель:

```text
➕ Импорт | 📂 Открыть | 🔄 Обновить | ✏ Редактировать | 📋 Дублировать | 🗑 Удалить выбранный | 🧹 Очистить раздел | 🗑 Очистить всё | 📤 Экспорт | ⚙ Настройки
```

В текущем инкременте подключены безопасные операции:

- обновить;
- удалить выбранный dataset;
- очистить раздел;
- очистить все datasets проекта.

Импорт/редактирование/дублирование/экспорт остаются disabled до Dataset Import/Export Center.

## Plugin API Foundation

Sprint 1 закладывает только безопасный фундамент:

- plugin manifest;
- plugin status lifecycle;
- hooks registry;
- permissions/extension points;
- registry summary.

Исполнение стороннего plugin-кода в Sprint 1 запрещено.

## Далее

После завершения UMF начинается Sprint 1.5 Integration & Stabilization.
