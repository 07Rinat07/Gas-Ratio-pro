from __future__ import annotations

import html
import math
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

import pandas as pd

from .depth_track import build_depth_ticks
from .models import CompositeLogSpec, CurveTrackSpec, IntervalBand


@dataclass(frozen=True, slots=True)
class CompositeLogResult:
    svg: str
    width: int
    height: int
    depth_start: float
    depth_stop: float
    rendered_tracks: tuple[str, ...]
    issues: tuple[str, ...] = ()
    report_title: str = ""
    report_kind: str = "overview"
    report_intervals: tuple[dict[str, object], ...] = ()

    @property
    def figure(self) -> "CompositeLogResult":
        """Compatibility with the legacy presentation model plot wrapper."""
        return self


class CompositeLogEngine:
    """Build an engineering composite log as vector SVG.

    Every curve receives an independent track and scale. The shared vertical
    axis is depth, with explicit major/minor grid lines across the full log.
    The renderer is deterministic and suitable for browser preview and print.
    """

    def render(self, dataframe: pd.DataFrame, spec: CompositeLogSpec) -> CompositeLogResult:
        issues: list[str] = []
        depth_key = self._resolve_column(dataframe, spec.depth_key)
        if depth_key is None:
            raise ValueError(f"Depth column not found: {spec.depth_key}")

        frame = dataframe.copy()
        frame[depth_key] = pd.to_numeric(frame[depth_key], errors="coerce")
        frame = frame.loc[frame[depth_key].notna()].sort_values(depth_key)
        if frame.empty:
            raise ValueError("No numeric depth values available")

        depth_start = float(frame[depth_key].min())
        depth_stop = float(frame[depth_key].max())
        if depth_stop <= depth_start:
            raise ValueError("Depth range must be greater than zero")

        active_tracks: list[tuple[CurveTrackSpec, str]] = []
        for track in spec.tracks:
            column = self._resolve_column(frame, track.key)
            if column is None:
                issues.append(f"missing_curve:{track.key}")
                continue
            active_tracks.append((track, column))

        depth_width = spec.depth_track.width
        track_width = sum(track.width for track, _ in active_tracks)
        width = spec.left_padding + depth_width + track_width + spec.right_padding
        height = max(520, int(spec.height))
        plot_top = spec.header_height
        plot_bottom = height - spec.footer_height
        plot_height = plot_bottom - plot_top

        def y_for_depth(depth: float) -> float:
            ratio = (float(depth) - depth_start) / (depth_stop - depth_start)
            return plot_top + ratio * plot_height

        parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f'<rect x="0" y="0" width="{width}" height="{height}" fill="{spec.background}"/>',
            f'<style>text{{font-family:{html.escape(spec.font_family)};fill:#111827}} .small{{font-size:14px;font-weight:600}} .scale{{font-size:15px;font-weight:600}} .axis{{font-size:17px;font-weight:700}} .title{{font-size:24px;font-weight:800}} .interval-id{{font-size:14px;font-weight:700}} .interval-fluid{{font-size:14px;font-weight:800}} .stats-label{{font-size:14px;font-weight:800}} .stats-value{{font-size:13px;font-weight:700}}</style>',
            f'<text x="{spec.left_padding}" y="28" class="title">{html.escape(spec.title)}</text>',
        ]

        # Interval bands span all curve tracks and remain subordinate to curves.
        data_x = spec.left_padding + depth_width
        data_width = max(0, width - data_x - spec.right_padding)
        for interval in spec.intervals:
            top = max(depth_start, min(depth_stop, float(interval.top)))
            bottom = max(depth_start, min(depth_stop, float(interval.bottom)))
            if bottom <= top:
                continue
            y1, y2 = y_for_depth(top), y_for_depth(bottom)
            fill, stroke = self._fluid_style(interval.fluid)
            parts.append(
                f'<rect x="{data_x}" y="{y1:.2f}" width="{data_width}" height="{max(1.0, y2-y1):.2f}" fill="{fill}" fill-opacity="0.14" stroke="{stroke}" stroke-width="0.8"/>'
            )

        # Shared depth grid across all tracks.
        ticks = build_depth_ticks(
            depth_start,
            depth_stop,
            major_step=spec.depth_track.major_step,
            minor_divisions=spec.depth_track.minor_divisions,
        )
        for tick in ticks:
            y = y_for_depth(tick.value)
            stroke = spec.major_grid if tick.major else spec.minor_grid
            stroke_width = 1.0 if tick.major else 0.55
            parts.append(
                f'<line x1="{spec.left_padding}" y1="{y:.2f}" x2="{width-spec.right_padding}" y2="{y:.2f}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
            )
            tick_len = 9 if tick.major else 4
            parts.append(
                f'<line x1="{spec.left_padding + depth_width - tick_len}" y1="{y:.2f}" x2="{spec.left_padding + depth_width}" y2="{y:.2f}" stroke="#334155" stroke-width="{1.2 if tick.major else 0.7}"/>'
            )
            if tick.major:
                parts.append(
                    f'<text x="{spec.left_padding + depth_width - 12}" y="{y + 4:.2f}" text-anchor="end" class="axis">{tick.value:g}</text>'
                )

        # Depth track frame/header.
        parts.extend([
            f'<rect x="{spec.left_padding}" y="{plot_top}" width="{depth_width}" height="{plot_height}" fill="none" stroke="{spec.border}" stroke-width="1.2"/>',
            f'<rect x="{spec.left_padding}" y="34" width="{depth_width}" height="{spec.header_height-34}" fill="#f8fafc" stroke="{spec.border}" stroke-width="1"/>',
            f'<text x="{spec.left_padding + depth_width/2}" y="59" text-anchor="middle" class="axis">{html.escape(spec.depth_track.title)}</text>',
            f'<text x="{spec.left_padding + depth_width/2}" y="82" text-anchor="middle" class="scale">{html.escape(spec.depth_track.unit)}</text>',
        ])

        x = data_x
        rendered_tracks: list[str] = []
        for track, column in active_tracks:
            rendered_tracks.append(track.key)
            values = pd.to_numeric(frame[column], errors="coerce")
            finite = values[values.map(math.isfinite)]
            if finite.empty:
                issues.append(f"empty_curve:{track.key}")
                x += track.width
                continue

            minimum = float(track.minimum) if track.minimum is not None else float(finite.min())
            maximum = float(track.maximum) if track.maximum is not None else float(finite.max())
            if math.isclose(minimum, maximum):
                pad = max(abs(minimum) * 0.05, 1.0)
                minimum -= pad
                maximum += pad

            def x_for_value(value: float) -> float:
                if track.scale == "log" and minimum > 0 and maximum > minimum and value > 0:
                    ratio = (math.log10(value) - math.log10(minimum)) / (math.log10(maximum) - math.log10(minimum))
                else:
                    ratio = (value - minimum) / (maximum - minimum)
                return x + max(0.0, min(1.0, ratio)) * track.width

            # Track background, frame and vertical quartile grid.
            parts.append(f'<rect x="{x}" y="{plot_top}" width="{track.width}" height="{plot_height}" fill="#ffffff" fill-opacity="0.72" stroke="{spec.border}" stroke-width="1"/>')
            for ratio in (0.25, 0.5, 0.75):
                gx = x + track.width * ratio
                parts.append(f'<line x1="{gx:.2f}" y1="{plot_top}" x2="{gx:.2f}" y2="{plot_bottom}" stroke="{spec.minor_grid}" stroke-width="0.6"/>')

            # Header and explicit independent scale.
            parts.append(f'<rect x="{x}" y="34" width="{track.width}" height="{spec.header_height-34}" fill="#f8fafc" stroke="{spec.border}" stroke-width="1"/>')
            parts.append(f'<text x="{x + track.width/2:.2f}" y="55" text-anchor="middle" class="axis">{html.escape(track.title)}</text>')
            if track.unit:
                parts.append(f'<text x="{x + track.width/2:.2f}" y="73" text-anchor="middle" class="scale">{html.escape(track.unit)}</text>')
            parts.append(f'<text x="{x + 6:.2f}" y="94" class="scale">{minimum:.3g}</text>')
            parts.append(f'<text x="{x + track.width - 6:.2f}" y="94" text-anchor="end" class="scale">{maximum:.3g}</text>')

            points: list[str] = []
            for depth, value in zip(frame[depth_key], values):
                if pd.isna(value) or not math.isfinite(float(value)):
                    continue
                points.append(f"{x_for_value(float(value)):.2f},{y_for_depth(float(depth)):.2f}")
            if len(points) >= 2:
                parts.append(
                    f'<polyline points="{" ".join(points)}" fill="none" stroke="{track.stroke}" stroke-width="{track.stroke_width}" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>'
                )

            if track.show_statistics:
                avg = float(finite.mean())
                stats_top = plot_bottom + 24
                for row_index, value in enumerate((minimum, avg, maximum)):
                    sy = stats_top + row_index * 20
                    parts.append(f'<text x="{x + track.width/2:.2f}" y="{sy:.2f}" text-anchor="middle" class="stats-value">{value:.4g}</text>')
            x += track.width

        # Interval cards are rendered inside the depth column so they remain readable
        # and never cover engineering curves.
        for interval in spec.intervals:
            top = max(depth_start, min(depth_stop, float(interval.top)))
            bottom = max(depth_start, min(depth_stop, float(interval.bottom)))
            if bottom <= top:
                continue
            y1, y2 = y_for_depth(top), y_for_depth(bottom)
            fill, stroke = self._fluid_style(interval.fluid)
            card_h = min(86.0, max(58.0, y2 - y1 - 8.0))
            card_y = max(plot_top + 4.0, min(plot_bottom - card_h - 4.0, (y1 + y2 - card_h) / 2.0))
            card_x = spec.left_padding + 8.0
            card_w = depth_width - 16.0
            parts.append(f'<rect x="{card_x:.2f}" y="{card_y:.2f}" width="{card_w:.2f}" height="{card_h:.2f}" rx="4" fill="#ffffff" fill-opacity="0.96" stroke="{stroke}" stroke-width="1.2"/>')
            parts.append(f'<text x="{card_x + card_w/2:.2f}" y="{card_y + 19:.2f}" text-anchor="middle" class="interval-id">{html.escape(interval.label)}</text>')
            parts.append(f'<text x="{card_x + card_w/2:.2f}" y="{card_y + 38:.2f}" text-anchor="middle" class="small">{top:g}–{bottom:g} м</text>')
            fluid_text = str(interval.fluid or "Интервал")
            parts.append(f'<text x="{card_x + card_w/2:.2f}" y="{card_y + 58:.2f}" text-anchor="middle" class="interval-fluid" fill="{stroke}">{html.escape(fluid_text)}</text>')
            if interval.confidence is not None and card_h >= 78:
                parts.append(f'<text x="{card_x + card_w/2:.2f}" y="{card_y + 76:.2f}" text-anchor="middle" class="interval-fluid" fill="{stroke}">{interval.confidence:.0f}%</text>')

        # Footer labels for the shared statistics table.
        stats_top = plot_bottom + 24
        for row_index, label in enumerate(("min", "avg", "max")):
            sy = stats_top + row_index * 20
            parts.append(f'<text x="{spec.left_padding + depth_width/2:.2f}" y="{sy:.2f}" text-anchor="middle" class="stats-label">{label}</text>')
        parts.append(f'<line x1="{spec.left_padding}" y1="{plot_bottom + 6:.2f}" x2="{width-spec.right_padding}" y2="{plot_bottom + 6:.2f}" stroke="{spec.border}" stroke-width="1"/>')

        parts.append('</svg>')
        return CompositeLogResult(
            svg="".join(parts),
            width=width,
            height=height,
            depth_start=depth_start,
            depth_stop=depth_stop,
            rendered_tracks=tuple(rendered_tracks),
            issues=tuple(issues),
        )

    @staticmethod
    def _resolve_column(dataframe: pd.DataFrame, requested: str) -> str | None:
        requested_normalized = str(requested).strip().lower()
        for column in dataframe.columns:
            if str(column).strip().lower() == requested_normalized:
                return str(column)
        return None

    @staticmethod
    def _fluid_style(fluid: str) -> tuple[str, str]:
        normalized = str(fluid or "").strip().lower()
        if "нефт" in normalized or "oil" in normalized:
            return "#22c55e", "#15803d"
        if "конден" in normalized or "condens" in normalized:
            return "#f59e0b", "#b45309"
        if "газ" in normalized or "gas" in normalized:
            return "#ef4444", "#b91c1c"
        return "#94a3b8", "#475569"
