# Visualization Interaction Session v101

`VisualizationInteractionSession` composes viewport, cursor and selection services into one renderer-neutral state contract.

It provides:

- synchronized viewport, cursor and selection state;
- cursor invalidation after viewport changes;
- delegated viewport and selection Undo/Redo;
- deterministic revision tracking;
- reset and compact serializable snapshots;
- no UI or renderer dependencies.

The session is intended for future Workspace Session, Event Bus and LAS Viewer adapters.
