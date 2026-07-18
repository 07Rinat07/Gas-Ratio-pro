# Журнал изменений GAS RATIO PRO

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
