# Gas Ratio Pro жоба жоспары

Жаңартылған күні: 18 шілде 2026 жыл. Белсенді жинақ: `v225.4`.

## Міндетті инженерлік қағидалар

- бір pipeline page geometry үшін жалғыз дереккөз болады;
- UI, PDF, DOCX, HTML, SVG және PNG renderer-neutral contracts қолданады;
- A4/A3 және пайдаланушы профильдері ең төмен оқылатын типографиканы сақтайды;
- multi-page preview бірінші бетке үнсіз қысқармайды;
- құжаттама мен нұсқаулықтар `ru / kk / en` тілдерінде синхронды жаңартылады.

## Аяқталған кезең — v225.4

- көрінетін Print Center физикалық пакетке қосылды;
- әр бетті қарау және нақты preflight жиынтығы қосылды;
- page-aware package v1.2 және preview contract v1.1;
- DOCX/HTML үшін тікелей multi-page preview;
- HTML/DOCX/PDF/assets үшін ортақ strict normalizer;
- жергіліктендірілген белгілер мен хабарлар;
- `bundle` сол payload-ты пайдаланады.

## Келесі рұқсат етілген кезең — Parity Gate & Legacy Export Retirement

1. UI, PDF, DOCX, HTML, SVG және PNG үшін автоматты parity матрицасын жасау.
2. A4/A3, екі бағдар, track partition, page count, geometry signature және page chrome тексеру.
3. Parity сәтті расталғаннан кейін ғана тәуелсіз static/Plotly fallback жолдарын жою.
4. Ең төмен өлшемдерді тексеретін пайдаланушы физикалық профильдерін қосу.
5. Тесттер мен үш тілдегі барлық құжаттаманы жаңарту.
