# Repository documentation layout

## Root directory policy

The project root is reserved for runtime, build, license, configuration, and primary README files.

Allowed Markdown files at the project root:

- `README.md`
- localized primary README files matching `README.<locale>.md`, for example `README.ru.md`, `README.kk.md`, and `README.en.md`

All other documentation must be stored under `docs/`.

Release notes and changelogs belong in `docs/archive/releases/`. Developer documentation belongs in `docs/developer/`; user documentation belongs in `docs/user/`; architecture and design records belong in their existing `docs/` sections.

Do not create temporary plans, audit notes, implementation notes, screenshots, or generated Markdown files at the project root.
