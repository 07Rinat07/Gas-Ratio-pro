# Print Center and direct multi-page preview

Revision: 3 · GAS RATIO PRO v225.5

## What changed

Professional Print Center is now connected directly to the physical page-aware package. Before export, the visible interface calculates and shows:

- A4/A3 format and orientation;
- DPI and the actual page count;
- package readiness;
- a selectable preview for every physical SVG page;
- the same track partition for PDF, SVG, PNG, DOCX, and HTML.

## Workflow

1. Select report sections, paper format, orientation, and document language.
2. Run **“Calculate exact physical package”**.
3. Verify the profile, page count, and every page in the preview selector.
4. Start PDF, DOCX, HTML, or combined PDF+DOCX export.
5. Do not start another export until the current package has finished.

## DOCX and HTML

DOCX and HTML receive the canonical `pages` array from preview contract version 1.1. Every entry contains the page index, physical size, track list, and completed SVG. These formats do not rebuild layout and never use the first-page field as a fallback.

## Languages

Track, curve, overlay, and page summaries, page labels, error messages, and package status are generated in the selected Russian, Kazakh, or English locale.

## Limitations

Single-page fallback is disabled. If the canonical page array is missing or differs from the declared `page_count`, the package is invalid and must not be silently exported as page one.

## Cross-format parity and user profiles

Before delivery, the package passes an automated parity gate. It compares page count, physical dimensions, track partition, and geometry signature across SVG, PNG, PDF, and the direct DOCX/HTML preview. Any mismatch blocks export.

The page settings allow selection of a built-in profile or persistence of a user A4/A3 profile. A profile stores paper, orientation, margins, DPI, minimum font, minimum track width, and maximum tracks per page. Readability values cannot fall below the certified baseline profile.

When SVG or PNG contains multiple pages, the application creates a ZIP bundle with one file per page and a `manifest.json`. Page one is no longer delivered as the complete document.
