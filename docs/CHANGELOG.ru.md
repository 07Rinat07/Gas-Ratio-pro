# Журнал изменений GAS RATIO PRO
## v225.10 — Field Calibration, Sensitivity & Report Authorization — 2026-07-18

- добавлен project-owned synthetic field-surrogate dataset для 10 методов;
- добавлены RMSE/MAE/bias, sensitivity и uncertainty envelopes;
- final-report authorization подключён до PresentationModel/renderer;
- method context и authorization evidence сохраняются в artifact/history;
- Professional Print Center получил read-only diagnostics на ru/kk/en;
- foundation Dual Water остаётся `blocked_final_report`;
- production formulas не изменялись.

- Итоговая проверка v225.10: **2896 passed, 0 failed**; Live Workbench Acceptance: **14/14**; numerical validation: **10/10**; field calibration: **10/10**; final-report authorization: **9/10**.

## v225.9 — Petrophysical Engine Validation Foundation — 2026-07-18

- зарегистрированы 10 петрофизических методов с provenance, units, applicability, limitations и report policy;
- добавлены 10 synthetic reference cases, numerical tolerances и uncertainty metadata;
- добавлен application-service validation gate, CLI и JSON evidence;
- calculation manifests содержат method provenance и contract fingerprint;
- foundation Dual Water блокируется для final report.
- A3 landscape renderer переведён на фактический page/frame size; графики и текстовые таблицы используют полную рабочую область.
- PDF/DOCX/HTML синхронизированы контрактом `print-readability/v1.1` и controlled visual baseline v225.9.

- итог: petrophysical gate 10/10, Live Workbench 14/14, полный regression suite **2881 passed, 0 failed**.

## v225.8 — Stable Promotion & Live Workbench Acceptance — 2026-07-18

- build channel переведён в `stable` после 14/14 live acceptance checks;
- добавлены real Streamlit server health gate и executable AppTest session;
- проверены build/source identity и пять областей Workbench;
- LAS command и LAS Workspace подтверждены без traceback;
- добавлены CLI, `run_app.ps1 -Acceptance`, machine-readable contract и JSON evidence;
- открыт следующий этап Petrophysical Engine Validation Foundation.

## v225.7 — Architecture Boundaries, Behavioral Contracts & Controlled Rebaseline

- Устранены девять architecture-boundary violations без отключения audit checks.
- Temporary-file lifecycle переведён на application service и `DeleteEngine`.
- Cache telemetry сделана session-scoped зависимостью application container.
- Route/startup/cache-coherence lifecycle передан application service.
- Все Streamlit rerun проходят через единый gate.
- 26 brittle source assertions заменены runtime/view-model behavior tests (18 legacy, Print Center contract и 7 PDF preview contracts).
- 13 visual contracts переведены на утверждённые semantic snapshots с SHA-256.
- Исторические version pins заменены current-build identity contracts.
- Все 51 legacy regression contracts закрыты с evidence и replacement contract.
- Добавлен корневой `BUILD_VERSION` как единый источник версии.
- Документация и инструкции синхронизированы на `ru/kk/en`.
- Полный regression suite: **2855 passed, 0 failed**; расширенный release-контур: **480 passed**.

## v225.6 — Physical Golden Baseline & Print Center Acceptance

- Зафиксированы SVG/PNG/PDF golden-artifacts для A4/A3 portrait/landscape.
- Добавлен end-to-end Professional Print Center acceptance runner.
- Исправлен PDF `LayoutError` для mixed-orientation physical preview.
- Все 51 legacy regression contract классифицированы в machine-readable registry без silent `xfail`.

Полная история: [CHANGELOG.md](CHANGELOG.md).
