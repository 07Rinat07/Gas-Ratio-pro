# SEG-Y adapter evaluation

## Decision

Use a two-layer implementation:

1. a dependency-free bounded scanner for the 3200-byte textual header and 400-byte binary header;
2. `segyio` as an optional lazy adapter for trace headers, geometry, slices, previews, and later controlled export.

SEG-Y Revision 2.1 is the normative target. Older revisions remain compatibility inputs.

## Why two layers

Workbench startup and project indexing must not depend on a compiled seismic library. The native scanner reads exactly 3600 bytes and reports sample interval, samples per trace, sample format, revision, extended-header count, fixed-length flag, and an estimated trace count where this can be calculated safely.

`segyio` remains isolated behind an adapter because geometry inference can fail for valid but irregular files. Future UI must allow `ignore_geometry`/manual header mapping rather than treating inferred inline/crossline geometry as authoritative.

## Licensing

`segyio` is LGPL and is approved only as an optional adapter. It is not vendored. Notices and source links must be preserved in distribution documentation.

## First increment limitations

- no trace amplitudes are loaded;
- no inline/crossline geometry is inferred;
- negative/variable extended textual header counts are reported, not guessed;
- unsupported sample format codes produce stable warnings;
- the official standard PDF is referenced but not redistributed automatically.
