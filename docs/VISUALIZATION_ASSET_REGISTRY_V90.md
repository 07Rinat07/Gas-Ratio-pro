# Visualization Asset Registry v90

## Назначение

`VisualizationAssetRegistry` формирует проверяемый набор артефактов из одного уже построенного `VisualizationScenePipelineResult`.

Реестр не пересчитывает Domain Model, Scene, Layout или Render Model. SVG и PDF создаются из одного pipeline и проходят общий renderer parity validator.

## Состав набора

- SVG preview;
- PDF preview;
- JSON Render Model;
- JSON geometry contract;
- machine-readable registry manifest.

Каждый asset содержит размер, SHA-256, geometry signature, renderer id и признак export readiness.

## Инвариант

```text
One pipeline result
        ↓
Render Model and Print Layout
        ↓
SVG and PDF renderers
        ↓
Visualization Asset Registry
```

Экспортный слой получает готовые файлы и metadata и не должен повторно строить Scene или Layout.
