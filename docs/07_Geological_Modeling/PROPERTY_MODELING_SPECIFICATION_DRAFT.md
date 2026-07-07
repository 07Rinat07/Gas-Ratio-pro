# Property Modeling Specification Draft

## Назначение

Документ описывает рабочее пространство моделирования свойств GAS RATIO PRO. Модуль предназначен для подготовки и управления кубами/свойствами литологии, фаций, песчанистости, пористости, проницаемости, насыщенности, флюидных контактов и геометрических свойств.

## Phase II — C.1 Foundation

Реализована базовая backend-структура:

- `projects/property_modeling_workspace.py`;
- `PropertyCubeSpec`;
- `FluidContactSpec`;
- `GeometryPropertySpec`;
- расчет `NG = If(Facies in sand_values, 1, 0)`;
- статистика свойств;
- manifest;
- Markdown-отчет;
- UI-ready таблицы.

## Доказательная база

Методика расчета кубов свойств, включая литологическое/фациальное моделирование, расчет куба песчанистости, пористости, проницаемости, флюидных контактов и геометрических свойств, опирается на материалы, сохраненные в `docs/sources/`.

## Phase II — C.2 Facies Modeling Workspace Foundation

The Facies Modeling Workspace extends the Property Modeling Workspace with a dedicated facies registry, zone settings, vertical proportion curves, facies statistics and simulation job metadata.

Implemented backend module: `projects/facies_modeling_workspace.py`.

Core entities:
- `FaciesDefinition`;
- `FaciesZoneSettings`;
- `VerticalProportionLayer`;
- `FaciesSimulationJob`;
- `FaciesModelingManifest`.

The module follows the property modeling workflow used in the provided methodology for facies modeling, vertical trends and property cube preparation. Source: `docs/sources/lab-4-property-cubes.pdf`.


## Phase II C.4 — Interpolation Engine Foundation

The interpolation engine provides the backend layer for transferring well/property samples into grid targets. The foundation includes regular grid generation, normalized sample models, nearest-neighbor interpolation, IDW interpolation, simple kriging foundation metadata, interpolation jobs, manifests, UI-ready tables and Markdown reports.

The module is intentionally deterministic and conservative so that future Kriging, SGS and co-kriging algorithms can reuse the same public API without breaking existing workflows.

## Phase II C.5 — Property Simulation Engine Foundation

Property simulation extends interpolation workflows with multiple stochastic realizations.

Supported foundation methods:

- Sequential Gaussian Simulation foundation for numeric property cubes;
- Sequential Indicator Simulation foundation for discrete facies/lithology cubes.

Each simulated cell stores:

- coordinates and grid indices;
- simulated value;
- method name;
- realization number;
- seed;
- base estimate;
- uncertainty;
- confidence.

Simulation jobs are stored in `property_simulation_engine.json` and can be used by future UI panels, reporting workflows and uncertainty analysis modules.

## C.6 Fluid Contacts & Geometrical Properties

The Property Modeling subsystem includes a dedicated foundation for fluid contacts and cell geometry properties.

### Fluid Contacts

Supported contact types:

- OWC — oil-water contact;
- GOC — gas-oil contact;
- GWC — gas-water contact;
- FWL — free water level;
- Custom contacts.

Each contact stores name, type, depth or surface reference, zone, segment, confidence, source and notes.

### Geometrical Properties

Supported foundation properties:

- Cell Height;
- Cell Volume;
- Bulk Volume;
- Depth;
- Elevation;
- Relative Depth;
- Above Contact;
- Contact Set.

### Contact Set Coding

The contact set foundation converts cells into simple zone classes:

- `1` — gas zone;
- `2` — oil zone;
- `3` — water zone;
- `0` — unknown zone.

The feature is designed as a backend layer for future UI visualization, reservoir volume calculations and geological modeling workflows.
