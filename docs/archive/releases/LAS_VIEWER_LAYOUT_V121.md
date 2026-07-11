# LAS Viewer Layout v121

Adds a renderer-neutral layout contract for the dedicated LAS Viewer.

Implemented operations:

- deterministic track order;
- positive width weights;
- track visibility;
- per-track curve order;
- independent curve visibility;
- serializable immutable state with revision tracking.

UI adapters must issue layout operations and render the resulting state. They
must not calculate track ordering, visibility invariants or width validation.
