# Presentation UI Integration v34

This increment adds a renderer-neutral UI adapter for the Professional Reporting System.

## Purpose

The application UI should not hardcode report profile names, MIME types, export file names or technical appendix behaviour. The UI now has a small pure-Python adapter that converts user controls into stable presentation export options.

## Added

- `reports/presentation_ui.py`
- Stable report profile options:
  - `engineering`
  - `expert`
- Stable export format options:
  - `html`
  - `pdf`
  - `docx`
  - `bundle`
- Safe report basename creation.
- Conversion from UI state to `PresentationExportOptions`.

## Engineering rule

The default UI profile must remain `engineering`. Technical diagnostics, raw dataframe dumps and calculation internals must only appear when the user explicitly selects the expert profile.

## Next step

Wire the Streamlit export panel to this adapter and the existing bundle exporter.
