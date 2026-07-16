"""Compatibility construction for ReportDesign across incremental upgrades.

The Streamlit entry point and the report engine can temporarily come from
neighbouring builds when a user extracts an update over an existing folder.
This module prevents a newly added optional field from crashing the whole
workspace and preserves the value on the resulting object for downstream code.
"""

from __future__ import annotations

import inspect
from typing import Any, TypeVar

from reports.report_designer import ReportDesign

T = TypeVar("T")


def construct_compatible_dataclass(design_type: type[T], /, **values: Any) -> T:
    """Construct ``design_type`` with supported fields and attach new optional fields.

    This is intentionally narrow: required/known constructor errors still surface.
    Only keyword arguments unknown to an older constructor are attached after
    construction. Frozen dataclasses are supported through ``object.__setattr__``.
    """

    parameters = inspect.signature(design_type).parameters
    supported = {name: value for name, value in values.items() if name in parameters}
    deferred = {name: value for name, value in values.items() if name not in parameters}

    instance = design_type(**supported)
    for name, value in deferred.items():
        object.__setattr__(instance, name, value)
    return instance


def build_report_design(**values: Any) -> ReportDesign:
    """Build ReportDesign without failing on a neighbouring legacy schema."""

    return construct_compatible_dataclass(ReportDesign, **values)
