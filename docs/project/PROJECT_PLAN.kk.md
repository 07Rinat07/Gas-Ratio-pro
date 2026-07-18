# Gas Ratio Pro жоба жоспары

Жаңартылған күні: 2026 жылғы 18 шілде. Белсенді құрастыру: `v225.8 stable`.

## Аяқталған инкремент — Stable Promotion & Live Workbench Acceptance

- кроссплатформалық acceptance runner қосылды;
- уақытша Streamlit server health gate-тен өтеді;
- ресми AppTest нақты Workbench session орындайды;
- build version, stable channel, абсолютті source path және entry-point SHA-256 расталды;
- Toolbar, Project Explorer, Workspace Host, Properties және Status Bar тексерілді;
- LAS command және LAS Workspace traceback-сіз орындалады;
- нәтиже: **14/14 acceptance checks passed**;
- Windows launcher `run_app.ps1 -Acceptance` режимін қолдайды;
- құжаттама мен нұсқаулық орыс, қазақ және ағылшын тілдерінде синхрондалды.

## Келесі рұқсат етілген инкремент — Petrophysical Engine Validation Foundation

1. Ағымдағы Method Registry және formula inventory бекіту.
2. Әр method ID-ді source, license, units және applicability domain-пен байланыстыру.
3. Reference dataset және expected result дайындау.
4. Numerical tolerance және uncertainty metadata анықтау.
5. Application-service validation gate және regression test іске асыру.
6. Бөлек бекітілген evidence болмаса Interpretation 2.0 немесе visual baseline өзгертпеу.

## Definition of Done

- build channel `stable` болып қалады;
- live acceptance жергілікті қайталанып, 14/14 өтеді;
- әр petrophysical method machine-readable provenance иеленеді;
- validation dataset тексерілмеген немесе заңсыз алынған деректерді қамтымайды;
- нәтиже бекітілген tolerance ішінде қайталанады;
- README, instructions, status, roadmap, changelog, release notes және manifest `ru/kk/en` тілдерінде синхрондалды.
