# Stable-релиз и проверка Workbench

Revision: 1. Актуально для Gas Ratio Pro `v225.8`.

## Обычный запуск

```powershell
.\run_app.ps1 -ForceRestart
```

Launcher читает версию из `BUILD_VERSION`, проверяет занятый порт, очищает Python cache при принудительном перезапуске и запускает `app/streamlit_app.py` из текущего каталога проекта.

## Автоматическая проверка stable-релиза

```powershell
.\run_app.ps1 -ForceRestart -Acceptance
```

Проверка временно запускает Streamlit на loopback-порту и подтверждает:

- health endpoint;
- версию и абсолютный путь исходного кода;
- Toolbar;
- Project Explorer;
- Workspace Host;
- Properties;
- Status Bar;
- выполнение команды LAS;
- открытие LAS Workspace без traceback.

JSON-отчёт сохраняется в `artifacts/acceptance/live_workbench_acceptance.json`. Stable-релиз считается подтверждённым только при результате `passed: true` и прохождении всех проверок.

## Ограничения

Acceptance не импортирует и не изменяет пользовательские LAS-файлы. Используется текущий проектный metadata-контекст и безопасная навигация Workbench. Временный сервер всегда останавливается после проверки.
