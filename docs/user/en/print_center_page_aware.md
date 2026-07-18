# Print Center, physical pages, and visual-baseline control

Revision: 5 · GAS RATIO PRO v225.7

## Main user workflow

1. Select A4/A3, orientation, document language, and a built-in or user profile.
2. Select **Calculate exact physical package**.
3. Review page count, every SVG page, and the cross-format parity status.
4. Run PDF, DOCX, HTML, SVG/PNG, or combined export.
5. If parity fails, do not replace baselines manually; save diagnostics and recalculate after correcting the source settings.

## One package

PDF, SVG, PNG, DOCX, and HTML consume one page-aware package. DOCX/HTML receive the canonical `pages` array; repagination and first-page fallback are forbidden. Multi-page SVG/PNG is delivered as a ZIP with `manifest.json`.

## Readability

In v225.7 PDF and DOCX consume one print-readability contract. Minimum legend fonts, raster dimensions, and the one-item-per-row legend layout are validated automatically. A user profile cannot weaken the safe A4/A3 floors.

## Visual baseline

The four A4/A3 physical golden profiles remain protected by SVG/PNG/PDF checks. In addition, 13 historical visual tests now use a semantic rebaseline: depth range, intervals, legends, headers, priority frame, ternary regions, and fill modes are checked instead of incidental internal trace counts.

## Languages

The interface, preview messages, instructions, and diagnostics are supported in Russian, Kazakh, and English.
