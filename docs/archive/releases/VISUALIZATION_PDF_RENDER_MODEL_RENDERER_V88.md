# Visualization PDF Render Model Renderer v88

## Purpose

The PDF adapter is the second concrete renderer that consumes the shared
`VisualizationRenderModel` contract. It does not inspect LAS payloads, scene
layers or layout objects and therefore cannot recalculate engineering geometry.

## Input contract

The renderer accepts `visualization.scene.pipeline.result` and reads only:

- `render_model.primitives`;
- `render_model.clip_regions`;
- `print_layout.pages`;
- print page metadata.

## Supported primitives

- rectangle;
- line;
- polyline;
- text;
- plot clipping regions.

The adapter applies the prepared print transformation from source pixels to
physical PDF points. A Unicode TrueType font is registered when a configured or
common DejaVu/Noto/Windows font is available.

## Output contract

`PdfRenderModelResult` contains the binary PDF artifact and a serializable QA
summary with primitive count, clip count, page geometry, byte size, SHA-256,
font name and issues.

## Architectural boundary

```text
Domain Model -> Scene -> Layout -> Render Model -> PDF Renderer
```

The PDF renderer is intentionally independent from the existing report PDF
renderer. It renders visualization primitives only and is ready for later
embedding into report/export bundles.

## Next step

Add cross-renderer geometry signatures so SVG and PDF adapters can prove that
they consumed the same primitive ids, clipping regions and physical page
contract. Then connect the visualization PDF artifact to bundle assets without
rebuilding the scene.
