# Import profiles

An import profile stores safe preview and import settings for one data format. Profiles are project-scoped and never modify source files.

## Main capabilities

- format and scanner-version selection;
- LAS strict/tolerant mode;
- DLIS logical file/frame/channel settings;
- SEG-Y header-byte settings;
- reuse during batch import;
- readiness score before downstream processing.

The preview cache is keyed by file SHA-256, profile identifier and scanner version. Changing any component triggers a new scan.
