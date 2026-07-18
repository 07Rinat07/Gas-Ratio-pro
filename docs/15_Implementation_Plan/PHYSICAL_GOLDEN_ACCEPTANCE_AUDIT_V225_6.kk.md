# v225.6 іске асыру жоспары — Golden artifacts, Print Center acceptance және legacy audit

## Мақсат

A4/A3 физикалық компоновкасын бекіту, нақты пайдаланушы экспорт жолын тексеру және 51 белгілі failure-ды басқарылатын шешімдер registry-іне айналдыру.

## Орындалды

1. Интервалдары бар он тректі fixture қосылды.
2. Төрт профиль үшін SVG/PNG/PDF golden-artifacts жасалды.
3. Generate/verify service және regeneration script қосылды.
4. Profile persistence бар end-to-end acceptance runner іске асырылды.
5. HTML/PDF/DOCX bundle және multi-page SVG/PNG ZIP тексерілді.
6. PDF frame ішіндегі raster preview scaling түзетілді.
7. 51 legacy contract silent `xfail` қолданбай жіктелді.
8. Құжаттама мен release metadata үш тілде синхрондалды.

## Тексеру нәтижесі

- 150 мақсатты тест өтеді.
- Толық suite: 2853 тест, 2802 өтеді, 51 мұраланған failure.
- Registry және нақты failure жинағы 1:1 сәйкес; жаңа regression жоқ.
