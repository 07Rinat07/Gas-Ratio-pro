## Current completed increment

Visualization Curve and Overlay Render Model v83 is implemented. Curve normalization,
depth mapping, interval band geometry and plot clipping are now completed before the
SVG renderer. Pipeline SVG output consumes `render_model.primitives`; direct Scene
rendering remains only as a temporary compatibility fallback.

## Next implementation step

Implement the Curve Engine quality layer: split polylines at missing values, clip curve
segments at plot boundaries, add optional fills and remove remaining curve calculations
from legacy renderer paths.

# Project Progress and Next Step

## Completed architecture milestones

Architecture Review completed the service boundary audit and confirmed the rules for the current Core Platform layer.

Core LTS Freeze completed after the architecture review and locked the current repository, service, storage lifecycle and application state boundaries.

Sprint 2 Workspace Framework completed the first Modern Workspace foundation: workspace controller flow, dashboard cards, project explorer shortcuts, create/open/close/delete smoke workflow and UI boundary tests.

## Completed LAS workspace milestones

LAS Workspace 3.0 UI entry point is available through the controller boundary.

LAS creation wizard UI saves created LAS working copies through `LasWorkspaceController.create_las_working_copy`.

Workspace Dashboard cards and Project Explorer shortcuts are rendered from manager/controller data without moving business logic into the UI.

Completed in v37: Workspace Session Manager for Modern UI.

The application can now capture, save, load and restore a lightweight workspace session: active project, well, LAS, workspace, selected intervals, active report, active plot, recent exports and window layout.

## Current P0 increment

PDF Unicode i18n and export QA are the current stabilization priority.

Completed in v42: progress-document tests now read `docs/PROJECT_PROGRESS_NEXT_STEP.md`, and the interval engineering HTML report shows the hydrocarbon summary expected by Engineering profile users.

Completed in v43: preflight diagnostics now include professional PDF/DOCX export backend readiness and Unicode PDF font readiness as non-blocking warnings. This keeps application startup stable while making missing export dependencies visible before the user runs a report export.

Completed in v44: DOCX export now has the same explicit dependency guard contract as PDF export, and `scripts/export_smoke.py` provides a reproducible multilingual HTML/PDF/DOCX bundle smoke command for P0 export QA.

Completed in v45: presentation exports now have a single renderer-neutral facade for HTML, PDF, DOCX and bundle modes. Export manifests are normalized through one helper while preserving backward-compatible fields for existing tests and UI code.

Completed in v46: release export QA now runs the multilingual smoke bundle and validates the generated bundle manifest, referenced files, non-empty artifacts and cross-format consistency flags.

## Completed Modern Workbench foundation

Completed in v47: the first Modern Workbench shell foundation is available as framework-neutral core code. `core.command_framework` defines command descriptors, registry execution and event publication. `core.workbench_shell` builds a serializable shell model with Project Explorer, Workspace Toolbar, Workspace Area, Properties and Status Bar regions using application state and lightweight workspace session keys.

Completed in v48: the Workbench shell now includes a framework-neutral navigation model and dock layout model. Navigation entries describe available workspaces, while dock panes describe panel placement, size and collapsed state without placing business logic in the UI layer.

Completed in v49: the Workbench shell now includes a framework-neutral interaction state for the active navigation entry and active dock pane. Saved selections are restored only when they still match visible enabled navigation items and non-collapsed panes; otherwise the model falls back to safe defaults for predictable session recovery.

Completed in v50: workspace sessions now persist and restore Workbench navigation, dock layout and active interaction selections. This keeps layout restoration inside the session boundary and prevents future Streamlit renderer code from owning Workbench state decisions.

Completed in v51: Workbench interaction actions now go through the Command Framework. Navigation selection and dock-pane activation publish command events and update persisted shell state through core handlers instead of direct UI mutation.

Completed in v52: the Modern Workbench shell now exposes a renderer contract for future Streamlit integration. The contract contains only presentation-safe payload sections: context, status, navigation, dock regions, panels, commands, interaction state and command-backed renderer actions. UI renderers can display this payload and submit command ids without owning business logic or persistence decisions.

Completed in v53: the first thin Streamlit Modern Workbench renderer adapter is available in `app.workbench_renderer`. It builds the renderer contract from session state, renders navigation and dock controls from contract payload, and dispatches all clicks through command-backed renderer actions instead of mutating Workbench state directly.

Completed in v54: the Modern Workbench now has a controller layer in `core.workbench_controller`. The controller coordinates renderer actions, Command Framework execution, shell rebuilding and renderer-contract refresh. It validates navigation and dock targets before state changes, so Streamlit adapters can remain thin presentation code.

Completed in v55: the Modern Workbench now has a lifecycle foundation. `core.workbench_lifecycle` manages initialization, workspace open and workspace close operations. `core.workbench_context` provides a lightweight WorkspaceContext and Selection Service for selected LAS/report/interval/plot references. Navigation, active panel, lifecycle and selection changes are published through the event bus, while Streamlit remains a renderer-only boundary.

## Next recommended increment

Start connecting domain services to the Workbench tools incrementally. The next safest step is a LAS Viewer data summary provider that reads normalized curve metadata through the existing LAS/workspace boundaries and exposes only lightweight renderer payloads. Keep `scripts/release_export_qa.py` as the release check before packaging builds.

## V56 Modern Workbench Tool Registry

Completed:
- Added `core/workbench_tools.py` with `WorkbenchToolDescriptor`, `WorkbenchToolRegistry` and `WorkbenchToolManager`.
- Added default engineering tool descriptors for Workspace Explorer, LAS Viewer, Log Viewer, Gas Ratio Analysis, Report Preview, Export and Settings.
- Added command-backed tool activation through `workbench.tool.activate`.
- Added renderer-facing `action.activate_tool` to the Workbench renderer contract.
- Added tool state persistence through Workspace Session.
- Added tests for registry, activation pipeline, renderer action dispatch and session restore.

Next step:
Connect the first real tool view models to the Workbench renderer, starting with LAS Viewer and Gas Ratio Analysis, while keeping Streamlit as a thin presentation adapter.



## V57 Workbench Tool View Contract

Completed:
- Added `core/workbench_tool_views.py` with renderer-neutral `WorkbenchToolViewModel` and `WorkbenchToolViewService`.
- Added per-tool readiness status, renderer hints, empty states and command-backed activation actions.
- Added `tool_views` to controller and Streamlit adapter view-model payloads.
- Added tests for tool view payload creation, LAS Viewer readiness state and controller integration.

## V58 Workbench Tool Content Providers

Completed:
- Added provider-based tool view enrichment for LAS Viewer, Gas Ratio Analysis and Report Preview.
- Added lightweight `content` payloads to the Workbench tool view contract.
- LAS Viewer now exposes selected project, well and LAS ids plus summary cards when LAS context exists.
- Gas Ratio Analysis now exposes selected intervals and waits for interval selection after LAS activation.
- Report Preview now exposes active report, plot and interval references plus an export action.
- Added regression tests for all first tool content providers.

Next step:
Connect LAS Viewer to normalized LAS curve metadata while keeping heavy parsing and engineering calculations outside renderer state.

## V59 Workbench Tool Actions

Completed:
- Added `core/workbench_tool_actions.py` with command-backed tool action requests.
- Added actions for opening LAS context, running gas ratio analysis, refreshing report preview and requesting report bundle export.
- Tool action requests validate lightweight `WorkspaceContext` state and publish `workbench.tool_action.executed` events.
- Tool views now expose concrete renderer actions while keeping Streamlit free of business logic.
- Added regression tests for LAS, gas-ratio, report-preview and export tool actions.

Next step:
Connect tool actions to lightweight workflow state so accepted actions update the selected LAS, selected intervals, active report, active tool and recent exports through core services instead of remaining passive request records.

## V60 Workbench Tool Workflow State

Completed:
- Accepted LAS open actions now update the active LAS context, Workbench selection and active LAS Viewer focus.
- Accepted gas ratio actions now merge selected interval ids into Workspace Session and focus the Gas Ratio Analysis tool.
- Accepted report preview actions now persist active report context and focus Report Preview.
- Accepted export actions now focus the Export tool and update lightweight recent export descriptors.
- Tool action results now return refreshed workspace context after state changes.
- Added regression tests for action-driven context, selection, active tool and session updates.

Next step:
Connect LAS Viewer to normalized LAS curve metadata through a provider/service boundary. The renderer should receive only lightweight curve summaries, depth range and quality flags, while parsing and heavy data tables remain outside UI state.

## V61 Workbench LAS Metadata Provider

Completed:
- Added `services/las_curve_metadata_service.py` for lightweight LAS metadata summaries.
- LAS Viewer now reads selected LAS metadata through `LasManagerService` and exposes only renderer-safe payloads.
- Added curve count, row count, depth curve, depth range, curve units and quality flags to the Workbench tool view contract.
- Kept raw LAS tables and engineering calculations outside renderer state.
- Added tests for the metadata service and LAS Viewer provider integration.

Next step:
Start Visualization Engine foundation with renderer-neutral curve track models and printable plot payloads while keeping plotting implementation outside Streamlit UI.

## V62 LAS Visualization Payload Foundation

Completed:
- Added `services/las_visualization_payload_service.py` for renderer-neutral LAS visualization payloads.
- Added printable track descriptors for gamma, gas, resistivity, porosity and other curves.
- Added sampled curve point payloads with depth axis, units, min/max values and decimation flags.
- LAS Viewer now exposes a lightweight `visualization` payload beside curve metadata.
- Kept plotting backend, Streamlit rendering and raw LAS dataframe data outside Workbench UI state.
- Added regression tests for visualization payload generation and LAS Viewer provider integration.

Next step:
Connect the visualization payload to a thin renderer adapter and then start building Visualization Engine 2.0 chart layout rules for professional LAS print/export output.

## V63 LAS Visualization Interval Overlays

Completed:
- Added renderer-neutral LAS interval overlay payloads to `LasVisualizationPayloadService`.
- Visualization payloads can now carry selected interval bands with top/base depth, label, fluid type, confidence and track scope.
- LAS Viewer passes Workbench selected intervals into the visualization payload without exposing raw LAS dataframes to UI state.
- Invalid or out-of-range interval ids are ignored safely and reported with `interval_overlays_empty` quality flag.
- Added regression tests for overlay generation and invalid interval handling.

Next step:
Connect the visualization payload to a thin renderer adapter and add chart layout rules for printable LAS tracks, including stable track order, axis descriptors and interval overlay rendering hints.

## V64 LAS Visualization Styling Contract

Completed:
- Added renderer-neutral curve axis metadata for LAS visualization payloads.
- Added track and curve style descriptors with palette keys, stroke, fill and line width hints.
- Added fluid interval overlay style descriptors for oil, gas, condensate, water and unknown intervals.
- Added print profile metadata for SVG/PDF-ready rendering without binding the service to a plotting backend.
- Added regression tests for axis metadata, style metadata and print profile payloads.

Next step:
Implement the first renderer adapter for LAS visualization payloads. It should render tracks from the contract only, without recalculating curves or interval overlays inside Streamlit.


V65 added LAS visualization sampling and data quality metadata for large LAS payloads.

## V66 LAS Visualization Renderer Ready Payload

Completed:
- Added renderer-ready legend entries for LAS curves and interpreted interval overlays.
- Added `visible_tracks` for default printable track visibility.
- Added compact `plot_summary` with depth range, track count, curve count, overlay count and renderer readiness.
- Kept all rendering decisions in the service contract and kept raw LAS dataframes outside UI payloads.
- Added regression tests for legend, visible tracks and plot summary.

Next step:
Implement the first thin renderer adapter for LAS visualization payloads using only `tracks`, `curves`, `overlays`, `legend`, `visible_tracks` and `plot_summary` from the contract.
### V67 LAS visualization SVG preview

- Added lightweight renderer-neutral SVG preview to LAS visualization payload.
- Preview includes tracks, sampled curves and interval overlays without raw DataFrame content.
- Added regression coverage for preview metadata and SVG output.

Next step: connect the SVG preview to report preview and printable visualization export flow.

## V68 Visualization Report Integration

Completed:
- Attached prepared Visualization Engine preview payloads to `PresentationModel`.
- Added `DocumentVisualizationPreview` to the shared EngineeringDocument contract.
- HTML reports now embed lightweight SVG previews directly from the document model.
- PDF and DOCX renderers preserve visualization preview placement with renderer-safe placeholders.
- Export figure counts now include visualization previews without recalculating LAS curves in renderers.
- Added regression tests proving reports consume prepared SVG previews and do not expose raw dataframe content.

Next step:
Add a dedicated visualization export artifact writer so SVG previews can be saved beside HTML/PDF/DOCX bundles and referenced from export manifests.


## V69 Visualization Export Manifest Contract

Completed:
- Added visualization preview audit metadata to HTML, PDF, DOCX and bundle export manifests.
- Manifests now record preview count, export readiness, preview formats, track/curve/overlay totals and raw-data safety flag.
- Bundle validation now checks the visualization preview consistency flag together with profile, table and figure consistency.
- Added regression coverage for visualization manifest propagation across the bundle export path.

Next step:
Add a dedicated visualization artifact writer that saves SVG previews beside export bundles and lets PDF/DOCX reference those prepared artifacts without rebuilding plots.

## V70 Visualization Bundle Assets

Completed:
- Added a dedicated visualization asset writer for bundle exports.
- SVG visualization previews are now saved as stable files under `assets/` beside HTML/PDF/DOCX outputs.
- Bundle manifests now reference the same shared visualization asset instead of relying only on embedded report content.
- Bundle validation checks visualization asset files for existence and non-empty content.
- Added consistency flags for visualization asset count and single shared visualization asset source.
- Added regression tests for visualization asset writing and validation.

Next step:
Use the exported visualization assets in PDF/DOCX renderers as real embedded images or linked report resources instead of placeholders.

## V71 Visualization Asset Index

Completed:
- Added a machine-readable visualization asset index for exported bundle assets.
- The index records visualization preview asset ids, roles, relative paths, file sizes, SHA-256 digests, SVG format and renderer metadata.
- Bundle manifests now reference `visualization_asset_index` so external tools and release QA can verify visualization artifacts without filesystem guessing.
- Release export QA now reports a compact visualization asset summary.
- Bundle validation checks the visualization asset index file together with report files and SVG preview assets.

Next step:
Use indexed SVG visualization assets as concrete inputs for PDF/DOCX renderers so printable formats can embed the prepared Visualization Engine output instead of keeping placeholders.


## V72 Bundle Validation Report

Completed:
- Added a machine-readable bundle validation report for release export QA.
- The report records schema, status, checked files, file sizes, missing files, empty files, consistency flags and issue list.
- `release_export_qa` now writes the validation JSON beside the bundle manifest and returns its path in the QA summary.
- Added regression coverage for CI-friendly validation report generation.

Next step:
Use indexed SVG visualization assets as concrete inputs for PDF/DOCX renderers so printable formats can embed the prepared Visualization Engine output instead of keeping placeholders.

## v73 Export Contract Schema

- Added formal presentation export contract validation for bundle manifests.
- Release QA now validates manifest schema, visualization asset index schema and validation report schema.
- Contract validation is filesystem-only and does not rebuild engineering calculations.
- This stabilizes the external bundle format before deeper Visualization Engine work.


## v74 Visualization Engine Core Foundation

Completed:
- Added an independent renderer-neutral `VisualizationEngineCore`.
- Added `VisualizationLayerManager` for deterministic curve and interval overlay layers.
- Added `DepthSynchronizationContract` so LAS tracks share one printable depth domain.
- LAS visualization payloads now expose an `engine_scene` contract for UI, reports and future renderers.
- The scene contract keeps UI layers from recalculating curves, overlays, legend or depth synchronization.

Next step:
Implement the first dedicated Visualization Engine renderer adapter that consumes `engine_scene` instead of legacy LAS payload fields.

## v75 Visualization Scene Pipeline

Completed:
- Added a renderer-neutral `VisualizationScenePipeline` above `VisualizationEngineCore`.
- Added `VisualizationSceneContext` so scene inputs carry track, curve, overlay and depth metadata through a stable pipeline contract.
- Added dedicated pipeline stages: context preparation, scene build and scene validation.
- LAS visualization payloads now expose `scene_pipeline` alongside the existing `engine_scene` contract.
- Added validation metadata for empty or invalid scenes without requiring UI or report renderers to inspect raw payloads.
- Added regression tests for valid LAS scene pipeline output and invalid empty payload diagnostics.

Next step:
Add the first renderer adapter that consumes `scene_pipeline.scene` directly and produces a printable SVG scene output from the engine contract.

## v76 Visualization SVG Scene Renderer

Completed:
- Added `VisualizationSvgSceneRenderer`, the first dedicated renderer adapter for Visualization Engine 2.0.
- The renderer consumes `scene_pipeline.scene` and does not read legacy LAS payload curves, tracks or overlays directly.
- Added printable SVG output with synchronized depth, track layout, curve layers and interval overlays.
- LAS visualization payloads now expose the adapter result under `scene_renderers.svg`.
- Invalid or empty scenes return a safe diagnostic SVG artifact instead of raising inside UI or report layers.
- Added regression tests for valid scene rendering, payload integration and invalid scene diagnostics.

Next step:
Route report and bundle visualization assets through `scene_renderers.svg` so exports stop using the legacy mini SVG preview generator.

## v77 Visualization Domain Model Foundation

Completed:
- Added source-neutral `VisualizationDomainModel` contracts for tracks, curves and interpreted depth intervals.
- Added `VisualizationDomainModelAdapter` as the source boundary between LAS payloads and Visualization Engine.
- Updated `VisualizationScenePipeline` to run `domain_model → context → scene → validation`.
- Pipeline results now expose the normalized domain model for QA and future adapters.
- Kept existing scene and SVG renderer contracts compatible.
- Added roadmap section before Layout Engine and regression tests for normalization and engine payload conversion.

Next step:
Implement the renderer-neutral Layout Engine. It should calculate track geometry, synchronized depth coordinates and axis regions from `VisualizationScene`, while SVG remains a drawing-only adapter.

## v79 Visualization Render Model Roadmap Update

Approved:
- Added a mandatory renderer-neutral Render Model layer after Layout Engine.
- Layout owns geometry only; it must not emit SVG, PDF or UI-specific structures.
- Render Model owns ordered drawing primitives, clipping references, style references and render diagnostics.
- Concrete renderers consume Render Model only and must not inspect Domain Model or Scene directly.
- Updated implementation order:
  1. Render Model foundation.
  2. Axis and Grid Model.
  3. Track and Curve primitives.
  4. Label and Legend primitives.
  5. Print Layout and renderer parity.
  6. Large LAS performance optimization.

Target pipeline:
`Source Adapter → Domain Model → Scene → Layout → Render Model → Renderer`

Next step:
Implement the first Render Model contracts and builder while keeping the existing SVG scene renderer compatible during migration.


## v80 Visualization Render Model Foundation

Completed:
- Added renderer-neutral `VisualizationRenderModel`, `RenderPrimitive` and `RenderClipRegion` contracts.
- Added deterministic `VisualizationRenderModelBuilder` between Layout and renderer backends.
- Scene Pipeline now runs `domain_model → context → scene → layout → render_model → validation`.
- Added canvas, track background, border, title and plot clipping primitives.
- Empty layouts now produce safe diagnostic primitives instead of renderer failures.
- Existing SVG scene renderer remains the compatibility path until curve, overlay, axis and grid primitives are complete.

Next step:
Implement Axis and Grid Model with major/minor ticks, depth labels, curve-axis metadata and print-safe line/text primitives.

## v81 Visualization Axis and Grid Engine

Completed:
- Added renderer-neutral `VisualizationAxisGridModel`, `AxisModel`, `AxisTick` and `GridLine` contracts.
- Added shared depth major/minor ticks and synchronized horizontal grid coordinates.
- Added per-curve linear and logarithmic axes with prepared tick labels and vertical grid coordinates.
- Added an explicit `axis_grid` stage to `VisualizationScenePipeline`.
- Render Model now emits print-safe line and text primitives for prepared axes and grids.
- Kept the current SVG scene renderer as a compatibility path while curve and overlay primitives are migrated.

Next step:
Implement Track and Curve primitives in Render Model, including polyline geometry, clipping, NaN gaps and interval overlay rectangles. Then migrate the SVG renderer to consume Render Model only.

## V82 Visualization Track Engine

Completed:
- Added `services/visualization_track_engine.py`.
- Added stable ordered track collection and per-track region contracts.
- Added renderer-neutral visibility, printable, pinned, group and active-track state.
- Added shared depth viewport metadata for every visible track.
- Added `track_model` between Axis/Grid and Render Model in the scene pipeline.
- Render Model now consumes Track Model visibility and exposes track-engine metadata.

Current pipeline:

```text
Domain Model -> Scene -> Layout -> Axis/Grid -> Track Model -> Render Model -> Renderer
```

Next step:
Move curve polylines and interval overlay rectangles into Render Model primitives.
After that, the SVG renderer can be migrated to consume Render Model only.
