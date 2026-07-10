# Visualization Selection Layer v99

Version 99 adds a renderer-neutral immutable selection layer above hit testing.

The service supports replace, add, toggle, remove and clear commands. Selection
items are created from normalized hit-test results and preserve stable primitive,
track and source-layer identifiers. State and commands are serializable for
future Workspace Session, Event Bus and UI adapters.

Selection rules remain outside UI code. No existing render-model or renderer
contract is changed.
