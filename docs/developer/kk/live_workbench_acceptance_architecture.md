# Live Workbench Acceptance архитектурасы

Revision: 1. Контракт: `gas-ratio-pro/live-workbench-acceptance/v1`.

## Компоненттер

- `services/workbench_live_acceptance.py` — orchestration, health polling, UI contract тексеруі және процесс cleanup;
- `scripts/run_live_workbench_acceptance.py` — кроссплатформалық CLI;
- `config/live_workbench_acceptance_contract_v225_8.json` — міндетті тексерулер және promotion policy;
- `run_app.ps1 -Acceptance` — Windows entry point;
- `tests/test_live_workbench_acceptance_v225_8.py` — интеграциялық regression contract.

## Екі тексеру қабаты

1. Нақты `python -m streamlit run` subprocess сервердің іске қосылып, `/_stcore/health` арқылы `ok` қайтаратынын растайды.
2. Ресми `streamlit.testing.v1.AppTest` орындалатын Streamlit сессиясын құрады, Workbench аймақтарын тексереді және LAS command navigation орындайды.

Тек HTTP 200 жеткіліксіз, себебі сессия қосылғанға дейін Streamlit скрипті орындалмауы мүмкін. Тек AppTest те жеткіліксіз, себебі launcher/server boundary дәлелденбейді.

## Promotion policy

11 check ID-дің барлығы міндетті. Silent skip тыйым салынған. Runtime identity абсолютті `PROJECT_ROOT`, `BUILD_VERSION`, `BUILD_CHANNEL` және entry point мәндерімен сәйкес болуы керек. Уақытша subprocess кез келген нәтиже кезінде `finally` ішінде тоқтатылуы тиіс.
