# GAS RATIO PRO өзгерістер журналы
## v225.9 — Petrophysical Engine Validation Foundation — 2026-07-18

- provenance, units, applicability, limitations және report policy бар 10 петрофизикалық әдіс тіркелді;
- 10 synthetic reference case, numerical tolerances және uncertainty metadata қосылды;
- application-service validation gate, CLI және JSON evidence қосылды;
- calculation manifests method provenance және contract fingerprint қамтиды;
- foundation Dual Water final report үшін бұғатталған.
- A3 landscape renderer нақты page/frame size қолданады; графиктер мен мәтіндік кестелер толық жұмыс frame-ын пайдаланады.
- PDF/DOCX/HTML `print-readability/v1.1` және controlled visual baseline v225.9 арқылы синхрондалған.

- қорытынды: petrophysical gate 10/10, Live Workbench 14/14, толық regression suite **2881 passed, 0 failed**.

## v225.8 — Stable Promotion & Live Workbench Acceptance — 2026-07-18

- 14/14 live acceptance check өткеннен кейін build channel `stable` күйіне ауыстырылды;
- real Streamlit server health gate және executable AppTest session қосылды;
- build/source identity және Workbench-тің бес аймағы тексерілді;
- LAS command және LAS Workspace traceback-сіз расталды;
- CLI, `run_app.ps1 -Acceptance`, machine-readable contract және JSON evidence қосылды;
- Petrophysical Engine Validation Foundation кезеңі ашылды.

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
