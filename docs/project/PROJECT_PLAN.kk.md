# Gas Ratio Pro жобасының жоспары

Жаңартылған күні: 18 шілде 2026 жыл. Белсенді жинақ: `v225.6`.

## Аяқталған кезең — v225.6

- төрт physical golden baseline: A4/A3 portrait/landscape;
- қайталанатын golden regeneration және checksum verification;
- толық Professional Print Center acceptance-path;
- нақты PDF frame бойынша raster preview auto-scale;
- барлық 51 legacy regression machine-readable аудиті;
- silent `xfail` қолданбайтын replacement policy;
- үш тілдегі құжаттама және release governance.

## Келесі рұқсат етілген инкремент — Legacy Contract Remediation

1. Audit policy талаптарын әлсіретпей architecture-boundary бұзушылықтарын түзету.
2. Brittle source assertions-ты view-model және runtime behavior тесттеріне көшіру.
3. Visual rebaseline-ды golden artifacts арқылы бекіту.
4. Obsolete tests тек replacement tests қосылғаннан кейін жойылады.
5. Full regression және stable promotion gate қайталанады.

## Definition of Done

- төрт golden profile manifest checksum өзгермей өтеді;
- E2E acceptance жарамды HTML/PDF/DOCX және SVG/PNG жасайды;
- әр legacy contract шешім мен replacement алады;
- release-blocking architecture debt нөлге тең;
- версия, нұсқаулықтар, status, roadmap, changelog және manifest `ru/kk/en` тілдерінде синхрондалған.
