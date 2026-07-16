"""Framework-neutral design tokens for GAS RATIO PRO UI Platform."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class ColorTokens:
    background: str = "#0B1220"
    surface: str = "#111B2E"
    surface_raised: str = "#18243A"
    border: str = "#2A3952"
    text: str = "#E8EEF7"
    text_muted: str = "#9FB0C7"
    primary: str = "#2F80ED"
    success: str = "#27AE60"
    warning: str = "#F2C94C"
    error: str = "#EB5757"
    info: str = "#56CCF2"

@dataclass(frozen=True, slots=True)
class SpacingTokens:
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24
    xxl: int = 32

@dataclass(frozen=True, slots=True)
class RadiusTokens:
    sm: int = 4
    md: int = 8
    lg: int = 12
    pill: int = 999

@dataclass(frozen=True, slots=True)
class ControlTokens:
    height_sm: int = 28
    height_md: int = 36
    height_lg: int = 44
    icon_sm: int = 14
    icon_md: int = 18
    icon_lg: int = 22

@dataclass(frozen=True, slots=True)
class DesignTokens:
    colors: ColorTokens = ColorTokens()
    spacing: SpacingTokens = SpacingTokens()
    radius: RadiusTokens = RadiusTokens()
    controls: ControlTokens = ControlTokens()

DARK_TOKENS = DesignTokens()
