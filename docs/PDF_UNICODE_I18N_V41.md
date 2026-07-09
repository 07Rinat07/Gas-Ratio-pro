# PDF Unicode and i18n policy

PDF reports must support Russian, Kazakh and English text. ReportLab built-in
fonts such as Helvetica must not be used for engineering report text because
those fonts do not contain the glyphs needed for Cyrillic/Kazakh output and can
render as black squares in PDF viewers.

The PDF renderer searches fonts in this order:

1. environment variables `GAS_RATIO_PRO_PDF_FONT` and `GAS_RATIO_PRO_PDF_FONT_BOLD`;
2. optional project-local open fonts under `assets/fonts/`;
3. common Linux fonts: DejaVu Sans and Noto Sans;
4. common Windows fonts: Arial, Segoe UI, Calibri;
5. common macOS fonts.

Do not copy proprietary system fonts into the repository. If project-local fonts
are added later, use open fonts with a compatible license and document the
license in `docs/`.
