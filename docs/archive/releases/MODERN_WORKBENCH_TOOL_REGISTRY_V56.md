# Modern Workbench Tool Registry V56

## Назначение

Версия V56 добавляет UI-нейтральный слой инструментов Workbench. Инструмент в этом слое — это не Streamlit-компонент, а сериализуемое описание инженерной возможности: LAS Viewer, Log Viewer, Gas Ratio Analysis, Report Preview, Export, Workspace Explorer или Settings.

## Компоненты

- `WorkbenchToolDescriptor` — метаданные инструмента.
- `WorkbenchToolRegistry` — централизованный реестр инструментов.
- `WorkbenchToolManager` — активация, деактивация, порядок открытых инструментов.
- `workbench.tool.activate` — command-backed активация инструмента.
- `action.activate_tool` — renderer action для UI-адаптеров.

## Состояние

Workbench сохраняет только легкое UI-состояние:

- `workbench_tools`;
- `workbench_active_tool`;
- `workbench_open_tools`;
- `workbench_tool_order`.

В эти ключи не записываются LAS dataframe, расчетные таблицы, графики или интерпретационные модели.

## События

Добавлены события:

- `workbench.tool.registered`;
- `workbench.tool.activated`;
- `workbench.tool.deactivated`;
- `workbench.active_tool.changed`.

## Интеграция

Renderer получает список инструментов, активный инструмент и открытые инструменты через Workbench renderer contract. UI не изменяет state напрямую: он отправляет `action.activate_tool`, а controller выполняет команду через Command Framework.

## QA

Проверено:

- регистрация инструментов;
- активация через Tool Manager;
- активация через Workbench Controller;
- renderer action pipeline;
- сохранение и восстановление tool state через Workspace Session;
- регрессия существующих Workbench тестов;
- release export QA.
