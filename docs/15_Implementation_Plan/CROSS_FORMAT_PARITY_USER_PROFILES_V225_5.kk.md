# v225.5 — Cross-format parity gate, legacy export тоқтатылуы және пайдаланушы профильдері

## Мақсат

SVG, PNG, PDF, DOCX және HTML үшін физикалық page-aware package-ті Professional Print Center-дің жалғыз көзі ету, формат айырмашылықтарын автоматты бұғаттау және сақталатын қауіпсіз A4/A3 профильдерін қосу.

## Іске асыру

1. `VisualizationCrossFormatParityGate` page count, физикалық өлшем, track partition, geometry signature және canonical preview pages мәндерін салыстырады.
2. `VisualizationPageAwarePackage` v1.3 үшін `export_ready` тек parity gate сәтті болса ғана true болады.
3. `UserPhysicalPrintProfileStore` пайдаланушы профильдерін JSON файлында сақтайды.
4. Пайдаланушы параметрлері базалық minimum font/line/track шектерін әлсірете алмайды.
5. Professional report және LAS Viewer `PageAwareStaticArtifact` пайдаланады.
6. Көпбетті SVG/PNG manifest бар ZIP-пакетпен беріледі; first-page fallback тыйым салынған.
7. Legacy CompositeLog static-export жұмыс жолынан алынды.
8. UI және құжаттама `ru/kk/en` тілдерінде синхрондалды.

## Definition of Done

- parity gate қате пакетті бұғаттайды;
- UI parity status және gate id көрсетеді;
- A4/A3 пайдаланушы профилі сақталып, layout-қа қолданылады;
- SVG/PNG беттерді жоғалтпайды;
- тесттер, build metadata және құжаттама v225.5 нұсқасына сәйкес.
