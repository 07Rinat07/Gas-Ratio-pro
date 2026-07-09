# Project Progress — Next Step

Current stage: Professional Reporting System / Presentation Layer.

Completed in v26:
- Added `reports/presentation_html.py`.
- Added a print-ready engineering HTML renderer that consumes `PresentationModel`.
- Added explicit engineering/expert profile selection.
- Added optional professional well-log plot embedding from the same presentation source.
- Added regression tests to prevent HTML rendering from reintroducing technical diagnostics into the default engineering report.

Next implementation step:
- Build PDF export on top of the same `PresentationModel` / presentation renderer contract.
- Keep the default report engineer-first: conclusions, intervals, confidence, recommendations and limitations before technical appendices.
