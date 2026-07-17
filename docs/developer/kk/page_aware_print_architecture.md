# Page-aware басып шығару архитектурасы

Revision: 1 · GAS RATIO PRO v225.3

## Жүйелік шекара

`VisualizationScenePipeline` 2.1 нұсқасындағы физикалық `VisualizationPrintLayout` есептейді. Әр бетте `content_bounds`, `header_bounds`, `footer_bounds`, `legend_bounds`, `track_ids` және `chrome_primitives` бар.

`chrome_primitives` үшін `coordinate_space=page_pt` қолданылады. SVG және PDF оларды қайта масштабтамай және content clip қолданбай салуы тиіс. PNG дайын SVG беттерінен жасалады.

## Бірыңғай пакет

`VisualizationPageAwarePackageBuilder` 1.1 нұсқасындағы бір пакетті құрады:

- барлық SVG беттері;
- барлық PNG беттері;
- бір көпбетті PDF;
- geometry signature v3;
- page chrome келісімшарты;
- QA нәтижесі.

`VisualizationPrintCenterService` ru/kk/en тілдеріндегі жергіліктендірілген жиынтықты және PDF, SVG, PNG, DOCX/HTML preview үшін бір output contract жасайды. Downstream қабаттарында layout-ты қайта құруға болмайды.

## Инварианттар

- бір pipeline геометрияның жалғыз көзі болып табылады;
- бет нөмірлері мен шартты белгілер барлық renderer-де бірдей координаттарды пайдаланады;
- page count және track partition барлық форматтарда сәйкес келеді;
- single-page fallback мәні `false`;
- legacy жолы parity тесттерінен кейін ғана жойылады.
