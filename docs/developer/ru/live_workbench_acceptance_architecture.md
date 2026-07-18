# Архитектура Live Workbench Acceptance

Revision: 1. Контракт: `gas-ratio-pro/live-workbench-acceptance/v1`.

## Компоненты

- `services/workbench_live_acceptance.py` — orchestration, health polling, UI contract inspection и очистка процесса;
- `scripts/run_live_workbench_acceptance.py` — кроссплатформенный CLI;
- `config/live_workbench_acceptance_contract_v225_8.json` — обязательный набор проверок и promotion policy;
- `run_app.ps1 -Acceptance` — Windows entry point;
- `tests/test_live_workbench_acceptance_v225_8.py` — интеграционный regression contract.

## Два уровня проверки

1. Реальный subprocess `python -m streamlit run` подтверждает, что сервер стартует и отвечает `ok` на `/_stcore/health`.
2. Официальный `streamlit.testing.v1.AppTest` создаёт исполняемую Streamlit-сессию, проверяет элементы Workbench и выполняет командную навигацию LAS.

HTTP 200 без AppTest недостаточен: Streamlit-скрипт может не выполниться до подключения сессии. AppTest без server health также недостаточен: он не доказывает работоспособность launcher/server boundary.

## Promotion policy

Все 11 check ID обязательны. Silent skip запрещён. Runtime identity должна совпадать с абсолютным `PROJECT_ROOT`, `BUILD_VERSION`, `BUILD_CHANNEL` и entry point. Временный subprocess должен быть остановлен в `finally` при любом результате.
