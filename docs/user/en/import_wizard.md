# Import Wizard

The Import Wizard moves a file through selection, metadata preview, configuration, quick quality checks, and Dataset registration.

## Batch import

Multiple files can be processed in one operation. A failure in one file does not stop the remaining files. Each item receives an independent status, error code, and registered Dataset identifier.

## Data readiness

A readiness score from 0 to 100 is calculated from metadata preview and quick QC. The statuses are `ready`, `review`, and `blocked`. The score is advisory and does not replace engineering review.

## Safety

Source files are preserved as immutable artifacts. Wizard state never contains file payloads, DataFrames, or third-party parser objects.
