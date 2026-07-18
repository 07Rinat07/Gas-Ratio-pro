# Gas Ratio Pro жобасының жоспары

Жаңартылған күні: 18 шілде 2026 жыл. Белсенді жинақ: `v225.5`.

## Міндетті инженерлік қағидалар

- бір pipeline физикалық геометрияның көзі болып табылады;
- `export_ready` үшін cross-format parity gate сәтті болуы міндетті;
- A4/A3 пайдаланушы профильдері readability floor талаптарын әлсірете алмайды;
- multi-page SVG/PNG бірінші бетке қысқартылмайды;
- құжаттама мен нұсқаулықтар `ru / kk / en` тілдерінде синхронды жаңартылады.

## Аяқталған кезең — v225.5

- SVG/PNG/PDF/DOCX/HTML parity gate;
- page-aware package v1.3;
- persistent user profiles;
- manifest-backed static bundles;
- CompositeLog static-export тоқтатылды;
- Professional Print Center parity status көрсетеді;
- тесттер мен үш тілдегі құжаттама жаңартылды.

## Келесі рұқсат етілген инкремент — Stage 4 Acceptance & Stable Promotion

1. Профиль жасау және таңдау пайдаланушы acceptance-path тексеруін орындау.
2. Нақты деректерде A4/A3 portrait/landscape және custom profiles тексеру.
3. Visual golden artifacts бекіту.
4. Қалған legacy test failures талдау.
5. Толық release gate өткеннен кейін ғана stable шығару.

## Definition of Done

- package parity автоматты расталған;
- физикалық профиль көрінеді және қайталанады;
- барлық форматта барлық бет сақталады;
- legacy first-page/static fallback жоқ;
- build metadata, README, нұсқаулықтар, status, roadmap, changelog және manifest синхрондалған.
