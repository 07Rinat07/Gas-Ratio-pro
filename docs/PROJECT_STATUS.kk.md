# Ағымдағы күй — v225.6

Жаңартылған күні: 18 шілде 2026 жыл.

## Белсенді кезең

**Stage 4 — Acceptance, Visual Baseline & Legacy Contract Audit / Stabilization & Release Audit.** Жинақ күйі: **release candidate v225.6**.

## Іске асырылды

- A4/A3 кітаптық және альбомдық бағдарлары үшін visual golden-artifacts бекітілді;
- manifest SVG, PNG және PDF файлдарын, физикалық өлшемдерді, беттеуді, track partition, page chrome және SHA-256 мәндерін тексереді;
- `scripts/regenerate_physical_golden_artifacts.py` қайталанатын скрипті қосылды;
- end-to-end `ProfessionalPrintCenterAcceptanceRunner` іске асырылды;
- acceptance-path пайдаланушы профилін сақтау мен таңдауды, visible preview, parity gate, HTML/PDF/DOCX bundle және SVG/PNG delivery жолын қамтиды;
- portrait physical preview landscape PDF есебіне салынғандағы `LayoutError` түзетілді;
- 51 legacy regression contract machine-readable audit registry-ге енгізілді;
- audit silent `xfail` және replacement contract жоқ тестті жоюға тыйым салады;
- пайдаланушы архивінде `.github/workflows` жоқ.

## Релизді тексеру

- мақсатты v225.6 acceptance/golden/audit және renderer/export жинағы: **150 passed**;
- толық regression suite: **2853 tests, 2802 passed, 51 failed**;
- 51 failure мұраланған registry-де ашық сақталады;
- жаңа v225.6 regression failures: **0**;
- Python compileall, құжаттама сілтемелері, manifest және архив: **сәтті**.

## Келесі кезең

9 расталған architecture-boundary debt-ті жабу және brittle source/visual assertions-ты бекітілген behavior/golden contracts-пен ауыстыру. Stable күйіне тек release-blocking debt нөл болғанда өтуге болады.
