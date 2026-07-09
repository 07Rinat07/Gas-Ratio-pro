# Project Progress — Next Step

Current stage: Professional Reporting System.

Completed in v25:
- Added `reports/presentation_model.py`.
- Introduced `PresentationModel` as the single presentation source for reports, plots, UI and future PDF/DOCX exporters.
- Connected `HydrocarbonReportPayload` to the presentation model.
- Added optional well-log plot composition through the same model.
- Added regression tests that prevent report/plot renderers from diverging from the HIE result.

Next implementation step:
- Build the first PDF-oriented renderer on top of `PresentationModel`.
- Keep HTML, PDF, DOCX and UI consuming the same interpretation sections.
