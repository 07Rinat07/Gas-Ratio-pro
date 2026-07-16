# GAS RATIO PRO Design System

The design system defines typography, spacing, colors, elevation, control sizes, icons, cards, tables, trees, charts, workspaces and accessibility requirements. Random colors, emoji icons and one-off component styling are prohibited in production screens. Dark, light and high-contrast themes derive from shared design tokens.

## UI Platform foundation (v222.56)

The first framework-neutral implementation lives in `ui_platform/` and defines design tokens, a theme registry, JSON-safe component specifications and a thin Streamlit adapter. New Workbench UI code should depend on these contracts instead of creating one-off styling. The first migrated control is the global language switcher, which now uses compact content-sized controls rather than full-width page buttons.
