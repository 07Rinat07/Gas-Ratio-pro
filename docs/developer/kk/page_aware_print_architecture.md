# Page-aware басып шығару және тікелей preview архитектурасы

Revision: 4 · GAS RATIO PRO v225.6

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

## Cross-format parity gate v1.0

`VisualizationCrossFormatParityGate` `VisualizationPageAwarePackageBuilder` ішінде орындалады. Ол layout, package pages, SVG root dimensions, PNG IHDR dimensions, PDF беттерінің нақты санын, canonical preview pages, track partition және geometry signature мәндерін салыстырады. `VisualizationPageAwarePackage.export_ready` үшін `parity_gate.ok=true` міндетті.

`VisualizationPageAwarePackage` v1.3 нұсқасына жаңартылды. `VisualizationPrintCenterSummary` және UI view model `parity_gate_id` және `cross_format_parity_passed` өрістерін жариялайды.

## Пайдаланушы физикалық профильдері

`UserPhysicalPrintProfileStore` `gas-ratio-pro.physical-print-profiles` JSON схемасын `data/user_preferences/physical_print_profiles.json` файлында сақтайды. `VisualizationPrintLayoutEngine` сериализацияланған `physical_profile` қабылдайды. A4/A3 пайдаланушы профильдері readability floor талаптарын күшейте алады, бірақ базалық шектеулерді әлсірете алмайды.

## Static-export тоқтатылуы

Professional report және LAS Viewer `build_page_aware_static_artifact()` пайдаланады. Бірбетті SVG/PNG тікелей, көпбетті нұсқа manifest бар ZIP ретінде беріледі. `reports.export_static` ішіндегі тәуелсіз CompositeLog SVG/PNG/PDF тармағы жойылып, legacy path-қа нақты тыйым енгізілді. Қалыпты Plotly графиктері Kaleido арқылы қалады және физикалық Print Center құжаты болып саналмайды.

## Physical golden artifacts v225.6

`VisualizationPhysicalGoldenArtifactService` бір он тректі renderer-neutral fixture-ді `a4_portrait`, `a4_landscape`, `a3_portrait` және `a3_landscape` профильдері үшін құрады. Әр физикалық бетке SVG және PNG, әр профильге бір көпбетті PDF сақталады. `manifest.json` SHA-256, point/pixel өлшемдерін, track partition, chrome primitive count, geometry signature және parity gate id бекітеді.

Эталон тек визуалдық review аяқталғаннан кейін `python scripts/regenerate_physical_golden_artifacts.py` командасымен жаңартылады. Қайта генерация тесті structural signature және visual checksum мәндерін салыстырады.

## End-to-end Print Center acceptance

`ProfessionalPrintCenterAcceptanceRunner` raw DataFrame-ді downstream жібермей application-level жолды орындайды: profile store → `ReportPageAwarePreviewService` → visible view model → `PresentationModel` → HTML/PDF/DOCX bundle → SVG/PNG static delivery. Нәтиже `print-center-acceptance-report.json` ретінде сақталады.

PDF үшін `_AutoScaleRasterImage` қосылды. Физикалық preview өлшемі `wrap()` ішінде нақты `avail_width` және `avail_height` арқылы есептеледі, сондықтан portrait/landscape комбинациялары ReportLab `LayoutError` туғызбайды.

## Legacy regression audit

`config/legacy_regression_contracts_v225_6.json` барлық 51 inherited failure-ды қамтиды. Әр contract category, disposition, severity, rationale және replacement contract өрістеріне ие. Policy silent `xfail`, architecture debt жасыру және тестті replacement жоқ жоюға тыйым салады.
