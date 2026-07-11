# Visualization Interaction Events v102

Version 102 adds a renderer-neutral event contract and dispatcher for viewport,
cursor and selection interactions.

The UI emits serializable events. `VisualizationInteractionEventDispatcher`
routes them to `VisualizationInteractionSession`, preserving the rule that
interaction logic remains outside presentation adapters.

Supported events:

- viewport command, undo and redo;
- selection command, undo and redo;
- cursor update and clear;
- full interaction reset.

Cursor update events require a render model at dispatch time. All contracts are
serializable and ready for a future application Event Bus or Workspace Session.
