# LAS Viewer Render Pipeline v122

`LasViewerRenderPipeline` applies the renderer-neutral LAS Viewer state before
scene construction. It synchronizes track order, width, track/curve visibility,
active objects and the interaction viewport with the existing visualization
pipeline. UI adapters only provide commands and display the resulting render
model.
