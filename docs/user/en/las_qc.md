# LAS Quality Control

**Revision:** 1

The LAS QC module checks depth, missing values, ranges, spikes, flat intervals, and measurement units. The check never modifies the source LAS file.

## Results

- `passed` — no critical deviations were detected;
- `warning` — warnings were detected;
- `failed` — errors require engineering review.

Every finding has a stable `QC-*` code shared by Russian, Kazakh, and English interfaces.
