"""Renderer-neutral viewport primitives for interactive visualization.

The module owns depth/screen coordinate transforms and immutable pan/zoom
operations. It has no UI or renderer dependencies, so the same contract can be
used by Streamlit, desktop, web-canvas, SVG and PDF preview adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Mapping


_EPSILON = 1e-12


@dataclass(frozen=True, slots=True)
class ViewportLimits:
    """Optional navigation limits expressed in domain (depth) coordinates."""

    minimum: float | None = None
    maximum: float | None = None
    minimum_span: float = 1e-6
    maximum_span: float | None = None

    @property
    def valid(self) -> bool:
        if self.minimum is not None and self.maximum is not None:
            if self.maximum <= self.minimum:
                return False
        if not isfinite(self.minimum_span) or self.minimum_span <= 0:
            return False
        if self.maximum_span is not None:
            if not isfinite(self.maximum_span) or self.maximum_span < self.minimum_span:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "minimum": self.minimum,
            "maximum": self.maximum,
            "minimum_span": self.minimum_span,
            "maximum_span": self.maximum_span,
            "valid": self.valid,
        }


@dataclass(frozen=True, slots=True)
class InteractiveViewport:
    """Immutable mapping between a depth interval and a vertical screen range."""

    domain_start: float
    domain_stop: float
    screen_start: float
    screen_stop: float
    inverted: bool = True
    unit: str = ""
    limits: ViewportLimits = field(default_factory=ViewportLimits)

    @property
    def domain_span(self) -> float:
        return self.domain_stop - self.domain_start

    @property
    def screen_span(self) -> float:
        return self.screen_stop - self.screen_start

    @property
    def valid(self) -> bool:
        values = (self.domain_start, self.domain_stop, self.screen_start, self.screen_stop)
        return (
            all(isfinite(value) for value in values)
            and self.domain_span > _EPSILON
            and abs(self.screen_span) > _EPSILON
            and self.limits.valid
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.viewport",
            "version": "1.0",
            "domain_start": self.domain_start,
            "domain_stop": self.domain_stop,
            "domain_span": self.domain_span,
            "screen_start": self.screen_start,
            "screen_stop": self.screen_stop,
            "screen_span": self.screen_span,
            "inverted": self.inverted,
            "unit": self.unit,
            "limits": self.limits.to_dict(),
            "valid": self.valid,
            "renderer_neutral": True,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InteractiveViewport":
        limits_value = value.get("limits")
        limits_mapping = dict(limits_value) if isinstance(limits_value, Mapping) else {}
        return cls(
            domain_start=_float(value.get("domain_start")),
            domain_stop=_float(value.get("domain_stop")),
            screen_start=_float(value.get("screen_start")),
            screen_stop=_float(value.get("screen_stop")),
            inverted=bool(value.get("inverted", True)),
            unit=str(value.get("unit") or ""),
            limits=ViewportLimits(
                minimum=_optional_float(limits_mapping.get("minimum")),
                maximum=_optional_float(limits_mapping.get("maximum")),
                minimum_span=_float(limits_mapping.get("minimum_span"), 1e-6),
                maximum_span=_optional_float(limits_mapping.get("maximum_span")),
            ),
        )

    def domain_to_screen(self, value: float, *, clamp: bool = False) -> float:
        """Map a domain value to a screen coordinate."""

        self._require_valid()
        domain_value = float(value)
        if clamp:
            domain_value = min(max(domain_value, self.domain_start), self.domain_stop)
        ratio = (domain_value - self.domain_start) / self.domain_span
        if not self.inverted:
            ratio = 1.0 - ratio
        return self.screen_start + ratio * self.screen_span

    def screen_to_domain(self, value: float, *, clamp: bool = False) -> float:
        """Map a screen coordinate back to a domain value."""

        self._require_valid()
        screen_value = float(value)
        low = min(self.screen_start, self.screen_stop)
        high = max(self.screen_start, self.screen_stop)
        if clamp:
            screen_value = min(max(screen_value, low), high)
        ratio = (screen_value - self.screen_start) / self.screen_span
        if not self.inverted:
            ratio = 1.0 - ratio
        return self.domain_start + ratio * self.domain_span

    def pan_domain(self, delta: float) -> "InteractiveViewport":
        """Shift the visible interval by a domain-coordinate delta."""

        self._require_valid()
        return self._with_interval(
            self.domain_start + float(delta),
            self.domain_stop + float(delta),
        )

    def pan_pixels(self, delta_pixels: float) -> "InteractiveViewport":
        """Shift the visible interval by a screen-space drag distance."""

        self._require_valid()
        domain_delta = float(delta_pixels) * self.domain_span / self.screen_span
        if self.inverted:
            domain_delta = -domain_delta
        return self.pan_domain(domain_delta)

    def zoom(self, factor: float, *, anchor_domain: float | None = None) -> "InteractiveViewport":
        """Zoom around a domain anchor; factor > 1 zooms in."""

        self._require_valid()
        zoom_factor = float(factor)
        if not isfinite(zoom_factor) or zoom_factor <= 0:
            raise ValueError("zoom factor must be a positive finite number")

        anchor = (
            float(anchor_domain)
            if anchor_domain is not None
            else (self.domain_start + self.domain_stop) / 2.0
        )
        relative = (anchor - self.domain_start) / self.domain_span
        requested_span = self.domain_span / zoom_factor
        span = self._bounded_span(requested_span)
        start = anchor - relative * span
        return self._with_interval(start, start + span)

    def zoom_at_screen(self, factor: float, screen_coordinate: float) -> "InteractiveViewport":
        """Zoom while keeping the domain value under the cursor stationary."""

        anchor = self.screen_to_domain(screen_coordinate, clamp=True)
        return self.zoom(factor, anchor_domain=anchor)

    def fit(self, domain_start: float, domain_stop: float) -> "InteractiveViewport":
        """Replace the visible domain interval and apply navigation limits."""

        return self._with_interval(float(domain_start), float(domain_stop))

    def contains_domain(self, value: float) -> bool:
        return self.domain_start <= float(value) <= self.domain_stop

    def contains_screen(self, value: float) -> bool:
        low = min(self.screen_start, self.screen_stop)
        high = max(self.screen_start, self.screen_stop)
        return low <= float(value) <= high

    def _with_interval(self, start: float, stop: float) -> "InteractiveViewport":
        if not isfinite(start) or not isfinite(stop) or stop <= start:
            raise ValueError("viewport interval must be finite and increasing")

        span = self._bounded_span(stop - start)
        center = (start + stop) / 2.0
        start = center - span / 2.0
        stop = center + span / 2.0

        minimum = self.limits.minimum
        maximum = self.limits.maximum
        if minimum is not None and maximum is not None and span > maximum - minimum:
            start, stop = minimum, maximum
        else:
            if minimum is not None and start < minimum:
                stop += minimum - start
                start = minimum
            if maximum is not None and stop > maximum:
                start -= stop - maximum
                stop = maximum
            if minimum is not None:
                start = max(start, minimum)
            if maximum is not None:
                stop = min(stop, maximum)

        if stop - start <= _EPSILON:
            raise ValueError("viewport limits produce an empty interval")

        return InteractiveViewport(
            domain_start=start,
            domain_stop=stop,
            screen_start=self.screen_start,
            screen_stop=self.screen_stop,
            inverted=self.inverted,
            unit=self.unit,
            limits=self.limits,
        )

    def _bounded_span(self, span: float) -> float:
        bounded = max(float(span), self.limits.minimum_span)
        if self.limits.maximum_span is not None:
            bounded = min(bounded, self.limits.maximum_span)
        if self.limits.minimum is not None and self.limits.maximum is not None:
            bounded = min(bounded, self.limits.maximum - self.limits.minimum)
        return bounded

    def _require_valid(self) -> None:
        if not self.valid:
            raise ValueError("interactive viewport is invalid")


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _optional_float(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
