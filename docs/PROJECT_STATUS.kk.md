# Ағымдағы күй — v225.7

Жаңартылған күні: 2026 жылғы 18 шілде.

## Белсенді кезең

**Stage 4 — Workbench UI Completion / Stabilization & Release Audit.** Құрастыру мәртебесі — **release candidate v225.7**.

## Іске асырылды

- audit policy әлсіретілмей тоғыз architecture-boundary бұзушылығы жойылды;
- уақытша файлдарды жою application lifecycle service деңгейіне ауыстырылып, `DeleteEngine` арқылы орындалады;
- cache telemetry контейнерде бір рет жасалып, service boundary арқылы беріледі;
- route lifecycle, startup diagnostics және cache coherence application service иелігіне берілді;
- тікелей `st.rerun()` тек бірыңғай rerun gate ішінде қалдырылды;
- 26 brittle source assertion орындалатын behavior contract тесттерімен ауыстырылды (18 legacy, бір Print Center contract және 7 PDF preview contract);
- 13 визуалдық legacy-тексеру бекітілген semantic snapshot-тарға көшірілді;
- `visual_rebaseline_contracts_v225_7.json` және SHA-256 валидациясы қосылды;
- алты тарихи version pin current-build identity contract-пен ауыстырылды;
- бес ескірген Workbench compatibility assertion runtime/view-model тексерулеріне ауыстырылды;
- 51 legacy regression contract-тың барлығында `resolved_in`, evidence және replacement contract бар;
- нұсқаның бірыңғай көзі — түбірдегі `BUILD_VERSION` файлы;
- пайдаланушы архивінде `.github/workflows` жоқ.

## Legacy regression күйі

- тіркелген контракттар: **51**;
- v225.7-де жабылғаны: **51**;
- белсенді legacy contract: **0**;
- silent `xfail` және replacement contract-сыз тест жоюға тыйым сақталады.

## Релизді тексеру

- кеңейтілген architecture/renderer/export/documentation жиыны: **480 passed**;
- толық regression suite: **2855 passed, 0 failed**;
- 51 legacy nodeid толық suite құрамына кіреді және replacement contract арқылы өтеді;
- v225.7 жаңа regression failure саны: **0**;
- Python compileall: **passed**; 92 салыстырмалы Markdown сілтемесі және 36 manifest жолы: **valid**.

Автоматтандырылған release gate өтті. Stable promotion тек live Workbench acceptance аяқталғанша бұғатталған.

## Келесі кезең

Толық regression audit орындау, қолданбаны `run_app.ps1 -ForceRestart` арқылы іске қосу, Workbench-тің бес аймағын тексеру және содан кейін ғана v225.7 нұсқасын release candidate күйінен stable күйіне ауыстыру туралы шешім қабылдау.
