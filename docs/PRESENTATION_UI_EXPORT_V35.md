# Presentation UI Export v35

This increment connects the Modern UI layer to the frozen Presentation Layer.

## Purpose

The UI must not know how HTML, PDF, DOCX or bundle reports are rendered. It
builds a normalized `PresentationExportUiState`, passes the selected
`PresentationModel` to the UI adapter, and receives a download-ready artifact.

## Added

- `PresentationUiExportArtifact`
- `build_ui_export_artifact(model, state)`
- Streamlit export controls for report profile and export format

## Profiles

- Engineering: default engineer-facing report without technical noise.
- Expert: engineering report plus diagnostic and technical appendices.

## Formats

- HTML
- PDF
- DOCX
- HTML + PDF + DOCX bundle
