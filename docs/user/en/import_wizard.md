# Import Wizard

The Import Wizard moves a file through selection, metadata preview, configuration, quick quality checks, and Dataset registration.

## Batch import

Multiple files can be processed in one operation. A failure in one file does not stop the remaining files. Each item receives an independent status, error code, and registered Dataset identifier.

## Data readiness

A readiness score from 0 to 100 is calculated from metadata preview and quick QC. The statuses are `ready`, `review`, and `blocked`. The score is advisory and does not replace engineering review.

## Safety

Source files are preserved as immutable artifacts. Wizard state never contains file payloads, DataFrames, or third-party parser objects.

## Batch import and background jobs

In Data Workspace, open the Professional Import Wizard, select multiple files, and press Start import. Each file is processed independently. The jobs table shows status, progress, successful items, and failed items. A completed job can retry only its failed files. Terminal history is stored in the project at `imports/history.jsonl`.
