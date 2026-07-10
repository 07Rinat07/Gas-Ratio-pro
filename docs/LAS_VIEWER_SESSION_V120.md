# LAS Viewer Session v120

Version v120 introduces the first renderer-neutral application state for the dedicated LAS Viewer.

The session combines:

- LAS project and file identity;
- available and visible tracks;
- available and visible curves;
- active track and curve;
- depth-limited interactive viewport;
- existing cursor, selection and viewport interaction state.

UI adapters only dispatch visibility and activation actions. Validation and state transitions remain in the service layer.
