# GAS RATIO PRO өзгерістер журналы

## v225.7 — Architecture Boundaries, Behavioral Contracts & Controlled Rebaseline

- Audit check өшірілмей тоғыз architecture-boundary бұзушылығы жойылды.
- Temporary-file lifecycle application service және `DeleteEngine` деңгейіне көшірілді.
- Cache telemetry application container ішіндегі session-scoped dependency болды.
- Route/startup/cache-coherence lifecycle application service иелігіне берілді.
- Барлық Streamlit rerun бірыңғай gate арқылы орындалады.
- 26 brittle source assertion runtime/view-model behavior test-пен ауыстырылды (18 legacy, бір Print Center contract және 7 PDF preview contract).
- 13 visual contract SHA-256 validation бар бекітілген semantic snapshot-қа көшірілді.
- Тарихи version pin current-build identity contract-пен ауыстырылды.
- 51 legacy regression contract evidence және replacement contract-пен жабылды.
- Түбірдегі `BUILD_VERSION` нұсқаның бірыңғай көзі ретінде қосылды.
- Құжаттама мен нұсқаулық `ru/kk/en` тілдерінде синхрондалды.
- Толық regression suite: **2855 passed, 0 failed**; кеңейтілген release жиыны: **480 passed**.

## v225.6 — Physical Golden Baseline & Print Center Acceptance

- A4/A3 portrait/landscape үшін SVG/PNG/PDF golden artifact қосылды.
- End-to-end Professional Print Center acceptance runner қосылды.
- Mixed-orientation physical preview үшін PDF `LayoutError` түзетілді.
- 51 legacy regression contract silent `xfail` қолданбай registry-ге енгізілді.
