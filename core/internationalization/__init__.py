"""Safe application internationalization primitives."""

from core.internationalization.language_registry import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    LanguageDefinition,
    normalize_language,
)
from core.internationalization.localization_service import LocalizationService

__all__ = [
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "LanguageDefinition",
    "LocalizationService",
    "normalize_language",
]
