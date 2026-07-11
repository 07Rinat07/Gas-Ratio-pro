# LAS Viewer selection synchronization v124

Version v124 adds a renderer-neutral selection synchronization service for the
LAS Viewer. A logical selection can be expanded to matching primitives in other
visible tracks by `source_layer_id`, producing non-printable overlay primitives
for UI renderers.

The service supports exact primitive selection, cross-track source-layer
matching, track filtering, deterministic ordering, diagnostics, and serialized
render-model/selection contracts. Selection matching and highlight styling stay
outside UI adapters.
