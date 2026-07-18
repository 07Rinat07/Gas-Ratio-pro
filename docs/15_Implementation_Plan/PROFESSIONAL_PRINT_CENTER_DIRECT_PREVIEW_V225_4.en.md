# v225.4 implementation plan — Visible Print Center and direct DOCX/HTML preview

Status: **COMPLETED**.

## Goals

1. Connect the physical package to the visible Print Center.
2. Show exact profile and every page before export.
3. Pass canonical multi-page preview to DOCX/HTML without rebuilding layout.
4. Forbid silent first-page fallback.
5. Synchronize `ru/kk/en` code and documentation.

## Implementation

- `ReportPageAwarePreviewService`;
- `ProfessionalPrintCenterViewModel`;
- page-aware package v1.2;
- preview contract v1.1;
- shared strict normalizer;
- Streamlit preflight and page selector;
- PDF/DOCX/HTML/bundle integration;
- trilingual summary/page/error labels.

## Acceptance gates

- every page is available to UI and downstream renderers;
- declared page count matches the canonical array;
- report payload contains no raw DataFrame;
- first-page field fallback is forbidden;
- documentation and version metadata are synchronized.
