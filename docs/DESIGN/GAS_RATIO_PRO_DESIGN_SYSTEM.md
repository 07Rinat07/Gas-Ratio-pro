# GAS RATIO PRO Design System

The design system defines typography, spacing, colors, elevation, control sizes, icons, cards, tables, trees, charts, workspaces and accessibility requirements. Random colors, emoji icons and one-off component styling are prohibited in production screens. Dark, light and high-contrast themes derive from shared design tokens.

## UI Platform foundation (v222.56)

The first framework-neutral implementation lives in `ui_platform/` and defines design tokens, a theme registry, JSON-safe component specifications and a thin Streamlit adapter. New Workbench UI code should depend on these contracts instead of creating one-off styling. The first migrated control is the global language switcher, which now uses compact content-sized controls rather than full-width page buttons.

## Report and print UX

Report configuration must be collapsed by default and expose one visually dominant action at a time. Status colours are reserved for actual success, warning and error states; explanatory content uses neutral surfaces. Printed plots use the corporate report theme with readable 9.5–15 pt typography, non-hairline traces, restrained grid lines and legends that wrap or grow rather than shrink below readable size.

## Developer diagnostics

The properties pane shows only a concise health summary by default. Runtime lifecycle, routing, cache, repository, memory and session tables are available only after the user explicitly enables advanced diagnostics.

## Print & Export Center

Печать является действием над текущим Workspace, а не постоянно занимающей место страницей настроек. На панели инструментов используется компактная команда с иконкой принтера. Настройки графика не смешиваются с настройками документа и принтера. Язык документа выбирается независимо от языка интерфейса.
