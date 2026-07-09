# Presentation HTML Renderer v26

`reports/presentation_html.py` renders a print-ready engineering HTML document from the immutable `PresentationModel`.

## Purpose

The renderer is the first PDF-oriented presentation renderer. It does not rerun hydrocarbon interpretation, interval detection, evidence analysis or plotting logic. It only consumes already prepared presentation sections:

- executive summary;
- interval cards;
- engineering tables;
- optional professional well-log plot;
- optional expert technical appendix tables.

## Profiles

### Engineering profile

Default user-facing report profile. It shows engineering conclusions first:

1. executive summary;
2. main intervals;
3. interval cards;
4. reasoning, recommendations and limitations;
5. optional professional well-log tablet.

Technical row counters, raw diagnostics and dataframe previews are not part of the first report experience.

### Expert profile

Expert profile includes the same engineering sections plus technical appendix tables for audit/debug workflows.

## Rule

All HTML/PDF/DOCX/UI renderers must consume `PresentationModel`. They must not rebuild interval classification or duplicate report selection rules.
