# GAS RATIO PRO өзгерістер журналы
## v225.12 — Calibration Package Trust & Review Workflow — 2026-07-18

- immutable operator package fingerprints үшін detached Ed25519 signatures қосылды;
- project/environment scope және validity periods бар application-scoped public-key trust registry қосылды;
- immutable reviewer decisions, package/key/signature revocations және expiry monitoring енгізілді;
- signed lineage және controlled `development → validation → production` promotions іске асырылды;
- environment state immutable promotion record-пен салыстырылады;
- strict production trust activation, `PresentationModel` және renderer алдында орындалады;
- project authorization, ExportArtifact және Export History v6 trust evidence сақтайды;
- Professional Print Center үш тілді trust/review workflow алды;
- private keys application/project/release boundaries ішінде тыйым салынған; default registry бос;
- production formulas өзгермеді; Foundation Dual Water `blocked_final_report` күйінде қалады.

- v225.12 қорытынды тексеруі: **2934 passed, 0 failed**; Live Workbench Acceptance: **14/14**; Stage 5.3 gate: signature **1/1**, reviewer approvals **2/2**, promotion transitions **2/2**, production trust **passed**, private keys persisted **0**.

## v225.11 — Operator Dataset Import & Calibration Comparison — 2026-07-18

- project-scoped операторлық calibration ZIP import қосылды;
- data-rights gate owner, legal basis, processing, derivative analysis, final-report use, redistribution және expiration мәндерін тексереді;
- package scope, SHA-256 checksums, sizes, method-registry fingerprint және formula-change prohibition блоктаушы шарттар болып табылады;
- бастапқы ZIP және үш JSON-келісім source/rights fingerprints арқылы өзгермейтін түрде сақталады;
- 10 әдіс бойынша baseline/operator және operator/operator comparison қосылды;
- versioned project authorization package final export алдында қолданылады;
- ExportArtifact және Export History v5 authorization package ID мен operator calibration fingerprint сақтайды;
- Professional Print Center ru/kk/en import, activation, comparison және diagnostics басқаруын алды;
- production formulas өзгермеді; foundation Dual Water `blocked_final_report` күйінде қалады;
- жеке оператор деректері релиз архивіне кірмейді.

- v225.11 қорытынды тексеруі: **2915 passed, 0 failed**; Live Workbench Acceptance: **14/14**; Stage 5.2 gate: import **1/1**, comparison **10/10**, authorization **9/9**.

## v225.10 — Field Calibration, Sensitivity & Report Authorization — 2026-07-18

- 10 әдіске project-owned synthetic field-surrogate dataset қосылды;
- RMSE/MAE/bias, sensitivity және uncertainty envelopes қосылды;
- final-report authorization PresentationModel/renderer-ден бұрын қосылды;
- method context және authorization evidence artifact/history ішінде сақталады;
- Professional Print Center ru/kk/en read-only diagnostics алды;
- foundation Dual Water `blocked_final_report` күйінде қалады;
- production formulas өзгертілмеді.

- v225.10 қорытынды тексеруі: **2896 passed, 0 failed**; Live Workbench Acceptance: **14/14**; numerical validation: **10/10**; field calibration: **10/10**; final-report authorization: **9/10**.

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
