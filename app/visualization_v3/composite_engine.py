from __future__ import annotations

import html
import math
from dataclasses import dataclass
from typing import Mapping

import pandas as pd

from .depth_track import build_depth_ticks
from .models import CompositeLogSpec, CurveTrackSpec


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
        return self


@dataclass(frozen=True, slots=True)
class LayoutMetrics:
    width: int
    height: int
    left: int
    right: int
    title_height: int
    header_height: int
    footer_height: int
    depth_width: int
    plot_top: int
    plot_bottom: int
    title_font: int
    track_font: int
    scale_font: int
    depth_font: int
    interval_font: int
    stat_label_font: int
    stat_value_font: int
    curve_width: float
    major_grid_width: float
    minor_grid_width: float

    @classmethod
    def from_spec(cls, spec: CompositeLogSpec, track_count: int) -> "LayoutMetrics":
        width = max(1600, int(spec.left_padding + spec.depth_track.width + sum(t.width for t in spec.tracks) + spec.right_padding))
        height = max(1600, int(spec.height))
        # Fonts are derived from the physical track width.  This prevents a large
        # canvas from shrinking fixed 5–6 px text to microscope size in PDF.
        average_track = max(140, (width - spec.left_padding - spec.right_padding - spec.depth_track.width) / max(1, track_count))
        track_font = int(max(34, min(62, average_track * 0.24)))
        scale_font = int(max(27, min(48, average_track * 0.18)))
        depth_font = int(max(31, min(54, spec.depth_track.width * 0.16)))
        title_height = max(90, int(height * 0.055))
        header_height = max(220, int(height * 0.125))
        footer_height = max(220, int(height * 0.14))
        plot_top = title_height + header_height
        plot_bottom = height - footer_height
        return cls(
            width=width,
            height=height,
            left=int(spec.left_padding),
            right=int(spec.right_padding),
            title_height=title_height,
            header_height=header_height,
            footer_height=footer_height,
            depth_width=int(spec.depth_track.width),
            plot_top=plot_top,
            plot_bottom=plot_bottom,
            title_font=int(max(48, min(78, height * 0.032))),
            track_font=track_font,
            scale_font=scale_font,
            depth_font=depth_font,
            interval_font=int(max(27, min(44, average_track * 0.16))),
            stat_label_font=int(max(25, min(39, average_track * 0.14))),
            stat_value_font=int(max(28, min(44, average_track * 0.16))),
            curve_width=max(3.0, min(6.0, average_track / 65)),
            major_grid_width=1.6,
            minor_grid_width=0.7,
        )


class CompositeLogEngine:
    """Deterministic page-aware vector renderer for engineering composite logs."""

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

        raw_depth_start = float(frame[depth_key].min())
        raw_depth_stop = float(frame[depth_key].max())
        depth_start = float(spec.depth_min) if spec.depth_min is not None else raw_depth_start
        depth_stop = float(spec.depth_max) if spec.depth_max is not None else raw_depth_stop
        depth_start = max(raw_depth_start, depth_start)
        depth_stop = min(raw_depth_stop, depth_stop)
        if depth_stop <= depth_start:
            raise ValueError("Depth range must be greater than zero")
        frame = frame.loc[frame[depth_key].between(depth_start, depth_stop)].copy()
        if frame.empty:
            raise ValueError("No data inside selected depth range")

        active_tracks: list[tuple[CurveTrackSpec, str]] = []
        for track in spec.tracks:
            column = self._resolve_column(frame, track.key)
            if column is None:
                issues.append(f"missing_curve:{track.key}")
                continue
            active_tracks.append((track, column))

        metrics = LayoutMetrics.from_spec(spec, len(active_tracks))
        width, height = metrics.width, metrics.height
        plot_height = metrics.plot_bottom - metrics.plot_top

        def y_for_depth(depth: float) -> float:
            ratio = (float(depth) - depth_start) / (depth_stop - depth_start)
            return metrics.plot_top + ratio * plot_height

        font = html.escape(spec.font_family)
        parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><!-- Depth -->',
            f'<rect width="{width}" height="{height}" fill="{spec.background}"/>',
            f'<text x="{metrics.left}" y="{int(metrics.title_height*0.66)}" font-family="{font}" font-size="{metrics.title_font}" font-weight="700" fill="#0f172a">{html.escape(spec.title)}</text>',
        ]
        if str(spec.report_kind).lower() == "overview":
            parts.append(f'<text x="{metrics.left}" y="{int(metrics.title_height*0.94)}" font-family="{font}" font-size="{metrics.scale_font}" font-weight="700" fill="#475569">Рабочий диапазон: {depth_start:g}–{depth_stop:g} м · автоматически по значимым газовым данным и УВ-интервалам</text>')
            legend_items = (("Газ", "#ef4444"), ("Газоконденсат", "#f59e0b"), ("Нефть", "#22c55e"), ("Переходная/прочее", "#94a3b8"))
            legend_x = max(metrics.left + 1550, width - metrics.right - 1450)
            legend_y = int(metrics.title_height * 0.64)
            for legend_label, legend_color in legend_items:
                parts.append(f'<rect x="{legend_x}" y="{legend_y-30}" width="34" height="34" rx="4" fill="{legend_color}" fill-opacity="0.34" stroke="{legend_color}" stroke-width="3"/>')
                parts.append(f'<text x="{legend_x+48}" y="{legend_y}" font-family="{font}" font-size="{metrics.scale_font}" font-weight="700" fill="#1e293b">{html.escape(legend_label)}</text>')
                legend_x += 235 if legend_label == "Газ" else (430 if legend_label == "Газоконденсат" else (245 if legend_label == "Нефть" else 0))

        data_x = metrics.left + metrics.depth_width
        data_width = max(0, width - data_x - metrics.right)

        header_y = metrics.title_height
        parts.extend([
            f'<rect x="{metrics.left}" y="{header_y}" width="{metrics.depth_width}" height="{metrics.header_height}" fill="#f1f5f9" stroke="{spec.border}" stroke-width="2"/>',
            f'<rect x="{metrics.left}" y="{metrics.plot_top}" width="{metrics.depth_width}" height="{plot_height}" fill="#ffffff" stroke="{spec.border}" stroke-width="2"/>',
            f'<text x="{metrics.left+metrics.depth_width/2}" y="{header_y+metrics.header_height*0.42}" text-anchor="middle" font-family="{font}" font-size="{metrics.track_font}" font-weight="700" fill="#0f172a">{html.escape(spec.depth_track.title)}</text>',
            f'<text x="{metrics.left+metrics.depth_width/2}" y="{header_y+metrics.header_height*0.70}" text-anchor="middle" font-family="{font}" font-size="{metrics.scale_font}" font-weight="600" fill="#334155">{html.escape(spec.depth_track.unit)}</text>',
        ])

        # Interpreted hydrocarbon zones are rendered as real bands, not hairline
        # separators.  On the overview page a dedicated marker lane in the depth
        # column keeps labels readable while the bands remain visible across all
        # tracks.
        visible_intervals: list[tuple[object, float, float, str, str]] = []
        minimum_band_px = 5.0 if str(spec.report_kind).lower() == "overview" else 3.0
        for interval in spec.intervals:
            top = max(depth_start, min(depth_stop, float(interval.top)))
            bottom = max(depth_start, min(depth_stop, float(interval.bottom)))
            if bottom <= top:
                continue
            y1, y2 = y_for_depth(top), y_for_depth(bottom)
            fill, stroke = self._fluid_style(interval.fluid)
            visual_height = max(minimum_band_px, y2-y1)
            center_y = (y1+y2)/2
            draw_y = max(metrics.plot_top, min(metrics.plot_bottom-visual_height, center_y-visual_height/2))
            opacity = 0.18 if str(spec.report_kind).lower() == "overview" else 0.11
            parts.append(f'<rect x="{data_x}" y="{draw_y:.2f}" width="{data_width}" height="{visual_height:.2f}" fill="{fill}" fill-opacity="{opacity}" stroke="{stroke}" stroke-opacity="0.78" stroke-width="2.2"/>')
            visible_intervals.append((interval, draw_y, visual_height, fill, stroke))

        if str(spec.report_kind).lower() == "overview" and visible_intervals:
            lane_x = metrics.left + 14
            lane_w = metrics.depth_width - 118
            min_gap = max(42.0, metrics.interval_font * 1.45)
            candidates = sorted(visible_intervals, key=lambda row: row[1] + row[2]/2)
            # Label the thickest/most representative zones when there are many
            # micro-intervals; all zones still remain visible as coloured bands.
            max_labels = max(8, min(22, int(plot_height / min_gap)))
            if len(candidates) > max_labels:
                ranked = sorted(candidates, key=lambda row: row[2], reverse=True)[:max_labels]
                candidates = sorted(ranked, key=lambda row: row[1] + row[2]/2)
            placed: list[tuple[object, float, float, str, str, float]] = []
            previous_y = metrics.plot_top - min_gap
            for interval, band_y, band_h, fill, stroke in candidates:
                desired = band_y + band_h/2
                label_y = max(desired, previous_y + min_gap)
                placed.append((interval, band_y, band_h, fill, stroke, label_y))
                previous_y = label_y
            overflow = previous_y - (metrics.plot_bottom - min_gap/2)
            if overflow > 0:
                placed = [(a,b,c,d,e,max(metrics.plot_top+min_gap/2,f-overflow)) for a,b,c,d,e,f in placed]
            for interval, band_y, band_h, fill, stroke, label_y in placed:
                band_center = band_y + band_h/2
                card_h = max(52, metrics.interval_font * 2.15)
                card_y = label_y - card_h/2
                fluid_text = str(interval.fluid or "Интервал")
                confidence_text = f" · {interval.confidence:.0f}%" if interval.confidence is not None else ""
                parts.append(f'<line x1="{data_x}" y1="{band_center:.2f}" x2="{metrics.left+metrics.depth_width-86}" y2="{label_y:.2f}" stroke="{stroke}" stroke-width="2.4"/>')
                parts.append(f'<rect x="{lane_x}" y="{card_y:.2f}" width="{lane_w}" height="{card_h:.2f}" rx="8" fill="#ffffff" fill-opacity="0.96" stroke="{stroke}" stroke-width="3"/>')
                parts.append(f'<rect x="{lane_x}" y="{card_y:.2f}" width="14" height="{card_h:.2f}" rx="5" fill="{fill}"/>')
                parts.append(f'<text x="{lane_x+25}" y="{card_y+metrics.interval_font*0.92:.2f}" font-family="{font}" font-size="{metrics.interval_font}" font-weight="800" fill="#0f172a">{html.escape(str(interval.label))}</text>')
                parts.append(f'<text x="{lane_x+25}" y="{card_y+metrics.interval_font*1.78:.2f}" font-family="{font}" font-size="{max(22,metrics.interval_font-4)}" font-weight="700" fill="{stroke}">{html.escape(fluid_text+confidence_text)}</text>')
        elif visible_intervals:
            for interval, band_y, band_h, fill, stroke in visible_intervals:
                label = str(interval.label)
                if interval.fluid:
                    label += f" · {interval.fluid}"
                if interval.confidence is not None:
                    label += f" · {interval.confidence:.0f}%"
                label_y = max(metrics.plot_top + metrics.interval_font, min(metrics.plot_bottom - 8, band_y + metrics.interval_font + 5))
                parts.append(f'<text x="{data_x+10}" y="{label_y:.2f}" font-family="{font}" font-size="{metrics.interval_font}" font-weight="700" fill="{stroke}" paint-order="stroke" stroke="#ffffff" stroke-width="5">{html.escape(label)}</text>')



        ticks = build_depth_ticks(depth_start, depth_stop, major_step=spec.depth_track.major_step, minor_divisions=spec.depth_track.minor_divisions)
        for tick in ticks:
            y = y_for_depth(tick.value)
            stroke = spec.major_grid if tick.major else spec.minor_grid
            sw = metrics.major_grid_width if tick.major else metrics.minor_grid_width
            parts.append(f'<line x1="{metrics.left}" y1="{y:.2f}" x2="{width-metrics.right}" y2="{y:.2f}" stroke="{stroke}" stroke-width="{sw}"/>')
            tick_len = 18 if tick.major else 9
            parts.append(f'<line x1="{metrics.left+metrics.depth_width-tick_len}" y1="{y:.2f}" x2="{metrics.left+metrics.depth_width}" y2="{y:.2f}" stroke="#1e293b" stroke-width="{2.0 if tick.major else 1.0}"/>')
            if tick.major:
                parts.append(f'<text x="{metrics.left+metrics.depth_width-25}" y="{y+metrics.depth_font*0.34:.2f}" text-anchor="end" font-family="{font}" font-size="{metrics.depth_font}" font-weight="700" fill="#111827">{tick.value:g}</text>')

        x = data_x
        rendered_tracks: list[str] = []
        for track, column in active_tracks:
            rendered_tracks.append(track.key)
            values = pd.to_numeric(frame[column], errors="coerce")
            finite = values[values.map(lambda v: pd.notna(v) and math.isfinite(float(v)))]
            minimum = float(track.minimum) if track.minimum is not None else (float(finite.min()) if not finite.empty else 0.0)
            maximum = float(track.maximum) if track.maximum is not None else (float(finite.max()) if not finite.empty else 1.0)
            if math.isclose(minimum, maximum):
                pad = max(abs(minimum) * 0.05, 1.0)
                minimum -= pad
                maximum += pad

            def x_for_value(value: float) -> float:
                if track.scale == "log" and minimum > 0 and maximum > minimum and value > 0:
                    ratio = (math.log10(value)-math.log10(minimum))/(math.log10(maximum)-math.log10(minimum))
                else:
                    ratio = (value-minimum)/(maximum-minimum)
                return x + max(0.0, min(1.0, ratio))*track.width

            parts.append(f'<rect x="{x}" y="{header_y}" width="{track.width}" height="{metrics.header_height}" fill="#f1f5f9" stroke="{spec.border}" stroke-width="2"/>')
            parts.append(f'<rect x="{x}" y="{metrics.plot_top}" width="{track.width}" height="{plot_height}" fill="#ffffff" fill-opacity="0.72" stroke="{spec.border}" stroke-width="2"/>')
            for ratio in (0.25, 0.5, 0.75):
                gx = x + track.width*ratio
                parts.append(f'<line x1="{gx:.2f}" y1="{metrics.plot_top}" x2="{gx:.2f}" y2="{metrics.plot_bottom}" stroke="{spec.minor_grid}" stroke-width="1"/>')

            parts.append(f'<text x="{x+track.width/2:.2f}" y="{header_y+metrics.header_height*0.38:.2f}" text-anchor="middle" font-family="{font}" font-size="{metrics.track_font}" font-weight="700" fill="#0f172a">{html.escape(track.title)}</text>')
            scale_text = f"{minimum:.3g} — {maximum:.3g}" + (f" {track.unit}" if track.unit else "")
            parts.append(f'<text x="{x+track.width/2:.2f}" y="{header_y+metrics.header_height*0.70:.2f}" text-anchor="middle" font-family="{font}" font-size="{metrics.scale_font}" font-weight="600" fill="#334155">{html.escape(scale_text)}</text>')

            points: list[str] = []
            if not finite.empty:
                for depth, value in zip(frame[depth_key], values):
                    if pd.isna(value) or not math.isfinite(float(value)):
                        continue
                    points.append(f"{x_for_value(float(value)):.2f},{y_for_depth(float(depth)):.2f}")
            if len(points) >= 2:
                parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{track.stroke}" stroke-width="{max(track.stroke_width,metrics.curve_width):.2f}" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>')
            elif finite.empty:
                issues.append(f"empty_curve:{track.key}")

            # Three stacked rows are legible after PDF scaling and never collide
            # horizontally with neighbouring tracks.
            avg = float(finite.mean()) if not finite.empty else 0.0
            footer_top = metrics.plot_bottom + 18
            parts.append(f'<rect x="{x}" y="{metrics.plot_bottom}" width="{track.width}" height="{metrics.footer_height}" fill="#ffffff" stroke="{spec.border}" stroke-width="2"/>')
            stats = (("min", minimum), ("avg", avg), ("max", maximum))
            row_h = max(46, int((metrics.footer_height-28)/3))
            for idx, (label, value) in enumerate(stats):
                cy = footer_top + idx*row_h + row_h*0.62
                parts.append(f'<text x="{x+12}" y="{cy:.2f}" font-family="{font}" font-size="{metrics.stat_label_font}" font-weight="700" fill="#475569">{label}</text>')
                parts.append(f'<text x="{x+track.width-12}" y="{cy:.2f}" text-anchor="end" font-family="{font}" font-size="{metrics.stat_value_font}" font-weight="700" fill="#0f172a">{value:.4g}</text>')
            x += track.width

        parts.append('</svg>')
        return CompositeLogResult(svg="".join(parts), width=width, height=height, depth_start=depth_start, depth_stop=depth_stop, rendered_tracks=tuple(rendered_tracks), issues=tuple(issues))

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
