# Current status after v34

## Completed

- Hydrocarbon Interpretation Engine v1.0 freeze.
- Presentation Layer v1 freeze gate.
- Unified HTML/PDF/DOCX bundle export.
- Presentation UI integration foundation.

## Current result

The reporting UI now has a renderer-neutral adapter in `reports/presentation_ui.py`.
UI controls can use stable report profiles and export formats without hardcoding renderer details in Streamlit code.

## Next implementation module

Modern UI / Workspace integration.

Priority tasks:

1. Wire the Streamlit report export panel to `reports.presentation_ui`.
2. Add a visible report profile selector: engineering / expert.
3. Add stable export actions for HTML, PDF, DOCX and bundle.
4. Keep technical diagnostics out of the default engineering view.
