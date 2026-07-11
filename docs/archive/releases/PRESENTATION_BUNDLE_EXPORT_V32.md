# Presentation Bundle Export v32

## Purpose

The Presentation Bundle Export writes the engineering report in HTML, PDF and DOCX from one `PresentationModel` source.

This is a consistency layer. It prevents the same hydrocarbon interpretation, interval cards, recommendations and limitations from being rebuilt separately for each output format.

## Main rule

Engineering content is assembled once:

```text
PresentationModel
        ↓
EngineeringDocument
        ↓
HTML / PDF / DOCX
```

Format renderers are only responsible for drawing the document. They must not rerun calculations, interval detection, rule evaluation or recommendation logic.

## Output

`export_presentation_bundle_package()` creates:

- `<base>.html`
- `<base>.pdf`
- `<base>.docx`
- `<base>.manifest.json`
- individual per-format manifests

The bundle manifest records:

- exported files;
- report profile;
- table titles;
- figure count;
- presentation schema;
- report metadata;
- consistency flags.

## Consistency checks

The exporter verifies that all output formats have:

- the same report profile;
- the same table composition;
- the same figure count.

If any renderer diverges, the bundle export fails instead of silently producing inconsistent reports.

## Engineering rationale

For field and office workflows, PDF, DOCX and HTML must not contain different interpretations for the same interval. The bundle export makes the report package reproducible and auditable.
