# Visualization Interaction Checkpoints v104

Version 104 adds renderer-neutral checkpoints for fast restoration of viewport,
selection and cursor state without replaying the complete interaction journal.

The bounded checkpoint store supports deterministic serialization, latest-state
restore and Workspace Session persistence. Journal replay can continue from the
stored `journal_position` in a later integration step.
