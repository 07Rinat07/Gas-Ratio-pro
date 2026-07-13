# Large-LAS Visualization Acceptance Gates

## Purpose

The benchmark verifies that dense LAS visualization remains bounded before a release. It measures the renderer-neutral scene pipeline and does not include browser or static-export rendering.

## Run

```bash
python scripts/run_large_las_benchmark.py --points 25000 100000 --curves 4
```

Optional JSON artifact:

```bash
python scripts/run_large_las_benchmark.py --output artifacts/performance/large-las.json
```

## Default gates

- cold pipeline: no more than 2.5 seconds;
- warm cached pipeline: no more than 0.35 seconds;
- peak traced memory: no more than 192 MiB;
- geometry reduction: at least 80%;
- second run must use the render-model cache.

Thresholds are release policy and can be overridden explicitly for constrained CI runners. The benchmark uses deterministic synthetic data and never changes engineering calculations.
