# Gas Ratio Pro жоба жоспары

Жаңартылған күні: 2026 жылғы 18 шілде. Белсенді құрастыру: `v225.7`.

## Аяқталған инкремент — v225.7

- 9 architecture-boundary бұзушылығы жойылды;
- lifecycle, cache telemetry, route/startup/cache coherence және rerun иелігі дұрыс қабаттарға ауыстырылды;
- 26 source assertion behavior contract-пен ауыстырылды (18 legacy, бір Print Center contract және 7 PDF preview contract);
- 13 visual contract semantic snapshot manifest-ке көшірілді;
- obsolete version pin current-build identity contract-пен ауыстырылды;
- 51 legacy contract evidence және replacement test-пен жабылды;
- `BUILD_VERSION` нұсқаның бірыңғай көзі болды;
- орыс, қазақ және ағылшын тіліндегі құжаттама мен нұсқаулық синхрондалды;
- толық regression suite аяқталды: **2855 passed, 0 failed**.

## Келесі рұқсат етілген инкремент — Stable Promotion & Live Workbench Acceptance

1. Қолданбаны `run_app.ps1 -ForceRestart` арқылы іске қосу.
2. Build және абсолютті runtime source path растау.
3. Toolbar, Project Explorer, Workspace Host, Properties және Status Bar тексеру.
4. Command-backed әрекеттер мен LAS Viewer-ді traceback-сіз тексеру.
5. Release-blocking failure болмаған жағдайда ғана v225.7 stable күйіне ауыстыру.

## Definition of Done

- 51 legacy contract-тың барлығы resolved;
- белсенді architecture-boundary debt нөлге тең;
- semantic visual snapshot SHA-256 validation-нан өтеді;
- толық suite жаңа failure көрсетпейді;
- live Workbench acceptance расталды;
- version, README, instructions, status, roadmap, changelog, release notes және manifest `ru/kk/en` тілдерінде синхрондалды.
