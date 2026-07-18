# Page-aware басып шығару және тікелей preview архитектурасы

Revision: 2 · GAS RATIO PRO v225.4

## Геометрияның бірыңғай көзі

`VisualizationScenePipeline` физикалық `VisualizationPrintLayout` v2.1 жасайды. `VisualizationPageAwarePackageBuilder` барлық SVG/PNG беттері, көпбетті PDF, geometry signature v3, page chrome және QA нәтижесі бар v1.2 пакетін құрады.

## Application bridge

`ReportPageAwarePreviewService` ағымдағы есеп `DataFrame`-ынан физикалық пакетке өтетін жалғыз шекара болып табылады. Ол `LasVisualizationPayloadService.build_from_frame()` шақырып, кейін `VisualizationPrintCenterService.prepare()` орындайды және renderer-neutral payload-ты `PresentationModel` моделіне қосады.

Шикі `DataFrame` жолдары downstream қабаттарына берілмейді.

## Preview contract v1.1

`visualization.preview.page-aware` канондық келісімшарты `pages` массивін қамтиды. Әр бетте `index`, `track_ids`, `width_pt`, `height_pt`, chrome primitives саны және дайын SVG бар. `single_page_fallback=false` және `legacy_svg_fallback_allowed=false` жалаушалары міндетті.

`reports.visualization_preview.normalize_visualization_preview()` — HTML, DOCX, PDF және asset export үшін ортақ қатаң нормализатор. Page-aware схема үшін канондық `pages` жоқ болса, ол compatibility `svg` немесе `page_svgs` өрістерін қолданбайды.

## Көрінетін Print Center

`build_professional_print_center_view()` бір prepared package-ті UI келісімшартына айналдырады: нақты профиль, күй, geometry signature және preview беттерінің толық тізімі. Streamlit нәтижені параметрлер сигнатурасы бойынша сақтайды және экспорт кезінде сол report payload-ты береді.

## Инварианттар

- бір pipeline және бір geometry signature;
- downstream ішінде layout қайта құрылмайды;
- DOCX/HTML барлық физикалық беттерді тікелей алады;
- `bundle` форматы сол пакетті пайдаланады;
- белгілер мен хабарлар `ru/kk/en` үшін синхрондалған;
- page count сәйкессіздігі preview дайындық күйін бұғаттайды;
- legacy static-export жолдары parity аудитінен кейін ғана жойылады.
