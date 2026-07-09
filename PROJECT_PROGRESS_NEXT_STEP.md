# Current status after v35

## Completed

- Hydrocarbon Interpretation Engine v1.0 freeze.
- Presentation Layer v1 freeze gate.
- HTML/PDF/DOCX/bundle export from one PresentationModel.
- Presentation UI integration foundation.
- Streamlit report export controls wired to the Presentation Layer adapter.

## Current result

The report workspace can expose engineer/expert profiles and HTML/PDF/DOCX/bundle
export actions without duplicating renderer logic in the UI.

## Next implementation module

Modern UI / Workspace shell.

Priority tasks:

1. Add a clean workspace header and report actions panel.
2. Add project reset/clear workflow with safe confirmation.
3. Add visual consistency rules for cards, tables and toolbar actions.
4. Keep calculations and interpretation behind controllers/services.
