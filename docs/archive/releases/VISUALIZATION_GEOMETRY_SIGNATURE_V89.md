# Visualization Geometry Signature v89

## Purpose

The geometry signature proves that independent renderers consumed the same renderer-neutral drawing contract. It is calculated before artifact encoding and therefore does not depend on SVG serialization, PDF compression, embedded fonts or binary metadata.

## Covered contract

The SHA-256 signature includes:

- printable and visible Render Model primitives;
- primitive identity, kind, track, clip and z-order;
- normalized primitive payload geometry;
- Render Model width and height;
- clip regions;
- page size, orientation and DPI;
- first-page bounds, source bounds, content bounds and content scale.

Numbers are normalized to six decimal places and mappings are serialized with deterministic key ordering.

## Renderer contract

SVG and PDF renderer results expose `geometry_signature`. `VisualizationRendererParityValidator` compares this value with the signature recalculated from the pipeline and reports:

- `expected_geometry_signature`;
- `rendered_geometry_signature`;
- `geometry_signature_match`;
- `renderer_parity_geometry_signature_missing` or `renderer_parity_geometry_signature_mismatch` when required.

## Boundary

The signature intentionally excludes renderer-specific bytes, color-space implementation, PDF compression and font embedding. These differences do not represent geometry drift.

## Next step

Attach the already generated visualization PDF artifact to report export bundles as a shared asset. The bundle must reuse the same pipeline Render Model and geometry signature rather than rebuilding Scene or Layout.
