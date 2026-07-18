# Current status — v225.4

Updated: 18 July 2026.

The **Visible Professional Print Center & Direct DOCX/HTML Preview** increment is complete:

- the visible Professional Print Center directly prepares `VisualizationPageAwarePackage`;
- exact A4/A3 profile, orientation, DPI, actual page count, and readiness are shown before launch;
- users can select and inspect every physical SVG page;
- `VisualizationPageAwarePackage` is v1.2 and the preview contract is v1.1;
- `ReportPageAwarePreviewService` builds the package from the current report `DataFrame` without passing raw rows downstream;
- HTML, DOCX, and PDF use one strict normalizer and the canonical `pages` array;
- downstream layout rebuilding and silent first-page fallback are forbidden;
- combined `bundle` export uses the same page-aware payload;
- summaries, page labels, and messages are localized in Russian, Kazakh, and English.

## Release governance

Current stage: **Stabilization & Release Audit**. **Release candidate v225.4** is being checked for multi-format parity, strict preview-contract behavior, synchronized trilingual documentation, and a reproducible release archive.

## Next approved increment

1. Prove visible-preview parity with PDF/DOCX/HTML/SVG/PNG automatically for A4/A3.
2. Remove remaining independent legacy static-export branches only after parity is proven.
3. Add user-defined physical profiles while preserving minimum approved typography.
4. Run a separate audit of obsolete legacy-UI test contracts.
## v225.4 verification

- 166 focused and governance tests pass;
- the complete 2838-test collection was executed in four balanced shards: 2787 passed, 51 failed;
- every one of the 51 failures was rerun against the clean v225.3 archive and reproduced unchanged; no new v225.4 regression failure was found;
- Python compileall passes;
- every relative Markdown link in README files and `docs/`, including archived plans, resolves correctly;
- the build remains a release candidate because 51 obsolete legacy contracts require a separate audit, but they do not block the verified v225.4 print/export increment.
