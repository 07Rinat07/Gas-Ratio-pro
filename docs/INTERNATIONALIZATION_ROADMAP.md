# GAS RATIO PRO — Three-language Internationalization Roadmap

Status: **APPROVED / PHASE II SHELL MIGRATION STARTED**

Supported product languages:

- Russian — `ru`;
- Kazakh — `kk`;
- English — `en`.

## 1. Scope

The language contract applies to:

- application interface, navigation, forms, tooltips, validation, warnings and user-facing diagnostics;
- user instructions, Quick Start, User Guide and Administrator Guide;
- generated PDF, DOCX, HTML and spreadsheet report labels;
- report templates and regulatory profile wording;
- onboarding, examples and release notes intended for end users.

Source datasets and stable technical identifiers are not translated. LAS/DLIS mnemonics, SEG-Y/RESQML/GRDECL names, units, file paths, IDs, project names, well names and imported metadata remain unchanged unless the user explicitly edits them.

## 2. Safety rules

1. Only allow-listed language codes are accepted: `ru`, `kk`, `en`.
2. Locale values such as `kk-KZ` are normalized to their supported base language.
3. Catalog paths are application-owned; user input must never become a filesystem path.
4. Translation values are plain text. They are never evaluated as Python, HTML or template code.
5. Dynamic values are inserted only through named placeholders and converted to strings.
6. Missing keys fall back to Russian; if the key is absent everywhere, the stable key is shown rather than crashing the UI.
7. HTML rendering remains escaped by default. Translation catalogs must not be treated as trusted HTML.
8. Logs and internal exception identifiers remain language-neutral; UI presentation maps them to localized messages.

## 3. Architecture

Implemented foundation:

```text
core/internationalization/
├── language_registry.py
└── localization_service.py

services/
└── localization_application_service.py

resources/i18n/
├── ru.json
├── kk.json
└── en.json
```

UI code must migrate from hard-coded text:

```python
st.button("Открыть")
```

to stable keys:

```python
st.button(i18n("common.open"))
```

Business and repository layers must not depend on translated labels. They return stable codes such as `project_not_found`; the presentation layer resolves those codes into localized messages.

## 4. Locale ownership and precedence

Language resolution order:

1. explicit user preference;
2. project report-language override for generated documents;
3. supported operating-system/browser locale on first launch;
4. Russian fallback.

User interface language and report language are separate settings. A Russian-speaking engineer may work in a Russian UI while generating an English or Kazakh report.

Project files should store only normalized locale codes, never translated language names.

## 5. Terminology governance

Create a reviewed petroleum terminology glossary with one approved term per concept and language. The glossary must distinguish:

- UI vocabulary;
- geology and geophysics terminology;
- petrophysics and well logging terminology;
- reservoir engineering terminology;
- Kazakhstan regulatory terminology;
- abbreviations and non-translatable mnemonics.

Machine translation may assist drafting but cannot approve domain terminology. Kazakh and English report wording requires review by competent domain speakers.

## 6. Documentation layout

```text
docs/user/ru/
docs/user/kk/
docs/user/en/
docs/admin/ru/
docs/admin/kk/
docs/admin/en/
```

Developer architecture documents may remain English-first during migration, but every end-user instruction must have three synchronized versions. Each translated document carries a source revision identifier so outdated translations are detectable.

## 7. Report localization

Reports use versioned locale-aware templates:

```text
report_profile
├── jurisdiction
├── template_version
├── content_locale
├── terminology_revision
└── effective_date
```

Requirements:

- Cyrillic-capable embedded fonts for PDF;
- DOCX style definitions supporting Russian and Kazakh glyphs;
- localized captions, headings, units explanations and validation messages;
- stable numerical formatting rules separated from text translation;
- explicit decimal/date formatting per report profile;
- no translation of original measured values or curve mnemonics.

## 8. Migration sequence

### Phase I — foundation — implemented

- supported language registry;
- JSON catalogs for `ru`, `kk`, `en`;
- deterministic fallback;
- safe named-placeholder formatting;
- catalog completeness diagnostics;
- lazy application-service boundary;
- unit and lifecycle tests.

### Phase II — application shell

Migrate, in order:

1. language selector and user preference persistence — implemented in v222.21;
2. Dashboard and Workbench shell — Workbench File/Project menus, Explorer search, empty workspace and Properties migrated in v222.22;
3. Project Explorer root actions — search, results, empty state and collapse/restore migrated in v222.22;
4. global dialogs, confirmations and validation;
5. Diagnostics user-facing labels.

### Phase III — engineering workspaces

Migrate LAS Editor, calculations, interpretation, correlation, reservoir passport, ranking, tablet and project database views module by module. A module is complete only when no user-facing literal remains outside approved catalogs.

### Phase IV — reports and instructions

- locale-aware PDF/DOCX templates;
- user and administrator instructions in three languages;
- terminology review workflow;
- translation revision checks in release gates.

### Phase V — future data modules

Every new DLIS, SEG-Y, GIS, HDF5/NetCDF, GRDECL, RESQML and 3D module must ship with all three language catalogs in the same change. New features cannot introduce Russian-only UI text.

## 9. Quality gates

Release validation must check:

- JSON validity and UTF-8 encoding;
- equal required-key coverage for all three catalogs;
- placeholder parity across languages;
- no duplicate or empty keys;
- no unsupported locale persisted in user/project settings;
- no unlocalized user-facing literals in migrated modules;
- PDF/DOCX glyph coverage for Kazakh characters;
- screenshot/manual acceptance in all three languages;
- layout resilience for longer English/Kazakh labels;
- search, sorting and case handling with Cyrillic text.

## 10. Definition of done

Three-language support is complete when a user can select `ru`, `kk` or `en`, navigate the entire application, read instructions, complete engineering workflows and generate a report without encountering mixed-language application text, except for explicitly non-translatable technical data.
