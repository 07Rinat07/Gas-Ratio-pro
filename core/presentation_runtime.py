from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from threading import RLock
from time import perf_counter
from typing import Callable, Generic, Mapping, MutableMapping, TypeVar

import pandas as pd


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RevisionSnapshot:
    """Immutable revision boundary for the engineering presentation pipeline.

    The ``*_revision`` aliases preserve compatibility with older Workbench
    callers and cached modules while the canonical field names remain short.
    """

    data: int = 0
    calculation: int = 0
    presentation: int = 0
    export: int = 0

    @property
    def data_revision(self) -> int:
        return self.data

    @property
    def calculation_revision(self) -> int:
        return self.calculation

    @property
    def presentation_revision(self) -> int:
        return self.presentation

    @property
    def export_revision(self) -> int:
        return self.export


class RevisionController:
    """Tracks independent invalidation boundaries without coupling them to widgets.

    A downstream revision is incremented when an upstream layer changes. This
    preserves monotonic versions and makes cache invalidation explicit.
    """

    def __init__(self, initial: RevisionSnapshot | None = None) -> None:
        self._snapshot = initial or RevisionSnapshot()
        self._lock = RLock()

    @property
    def snapshot(self) -> RevisionSnapshot:
        with self._lock:
            return self._snapshot

    def bump_data(self) -> RevisionSnapshot:
        with self._lock:
            current = self._snapshot
            self._snapshot = RevisionSnapshot(
                data=current.data + 1,
                calculation=current.calculation + 1,
                presentation=current.presentation + 1,
                export=current.export + 1,
            )
            return self._snapshot

    def bump_calculation(self) -> RevisionSnapshot:
        with self._lock:
            current = self._snapshot
            self._snapshot = RevisionSnapshot(
                data=current.data,
                calculation=current.calculation + 1,
                presentation=current.presentation + 1,
                export=current.export + 1,
            )
            return self._snapshot

    def bump_presentation(self) -> RevisionSnapshot:
        with self._lock:
            current = self._snapshot
            self._snapshot = RevisionSnapshot(
                data=current.data,
                calculation=current.calculation,
                presentation=current.presentation + 1,
                export=current.export + 1,
            )
            return self._snapshot

    def bump_export(self) -> RevisionSnapshot:
        with self._lock:
            current = self._snapshot
            self._snapshot = RevisionSnapshot(
                data=current.data,
                calculation=current.calculation,
                presentation=current.presentation,
                export=current.export + 1,
            )
            return self._snapshot


@dataclass(frozen=True, slots=True)
class RuntimeTiming:
    stage: str
    duration_ms: float
    cache_hit: bool = False


@dataclass(frozen=True, slots=True)
class WellLogRenderModel:
    """Renderer-neutral contract for a well-log presentation request."""

    source_signature: str
    calculation_revision: int
    presentation_revision: int
    depth_range: tuple[float, float] | None
    tracks: tuple[str, ...]
    height: int
    settings_signature: str
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ReportDocumentModel:
    """Renderer-neutral report contract used by PDF, DOCX and HTML exporters."""

    source_signature: str
    presentation_revision: int
    export_revision: int
    title: str
    profile: str
    sections: tuple[str, ...]
    figure_ids: tuple[str, ...] = ()
    table_ids: tuple[str, ...] = ()
    metadata: Mapping[str, str] = field(default_factory=dict)


def content_signature(value: object) -> str:
    """Return a stable SHA-256 signature for a path, uploaded file or bytes."""

    if isinstance(value, (str, Path)):
        path = Path(value)
        data = path.read_bytes()
    elif isinstance(value, (bytes, bytearray, memoryview)):
        data = bytes(value)
    elif hasattr(value, "getvalue"):
        data = bytes(value.getvalue())
    elif hasattr(value, "read"):
        position = value.tell() if hasattr(value, "tell") else None
        data = value.read()
        if position is not None and hasattr(value, "seek"):
            value.seek(position)
        data = bytes(data)
    else:
        raise TypeError("Unsupported content source for signature calculation.")
    return sha256(data).hexdigest()


def dataframe_signature(frame: pd.DataFrame) -> str:
    """Build a content-based signature without depending on Python object id."""

    digest = sha256()
    digest.update(str(tuple(frame.columns)).encode("utf-8"))
    digest.update(str(tuple(str(dtype) for dtype in frame.dtypes)).encode("utf-8"))
    digest.update(pd.util.hash_pandas_object(frame, index=True).values.tobytes())
    return digest.hexdigest()


class ParsedLasCache:
    """Small thread-safe LRU cache keyed strictly by LAS content signature."""

    def __init__(self, max_entries: int = 8) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        self.max_entries = int(max_entries)
        self._items: OrderedDict[str, dict[str, pd.DataFrame]] = OrderedDict()
        self._lock = RLock()

    @staticmethod
    def _copy_sheets(sheets: Mapping[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        copied: dict[str, pd.DataFrame] = {}
        for name, frame in sheets.items():
            clone = frame.copy(deep=True)
            clone.attrs = dict(frame.attrs)
            copied[str(name)] = clone
        return copied

    def get_or_load(
        self,
        source: object,
        loader: Callable[[object], Mapping[str, pd.DataFrame]],
    ) -> tuple[dict[str, pd.DataFrame], str, RuntimeTiming]:
        signature = content_signature(source)
        started = perf_counter()
        with self._lock:
            cached = self._items.get(signature)
            if cached is not None:
                self._items.move_to_end(signature)
                return (
                    self._copy_sheets(cached),
                    signature,
                    RuntimeTiming("parse", (perf_counter() - started) * 1000.0, True),
                )

        loaded = dict(loader(source))
        canonical = self._copy_sheets(loaded)
        with self._lock:
            self._items[signature] = canonical
            self._items.move_to_end(signature)
            while len(self._items) > self.max_entries:
                self._items.popitem(last=False)
        return (
            self._copy_sheets(canonical),
            signature,
            RuntimeTiming("parse", (perf_counter() - started) * 1000.0, False),
        )

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)


GLOBAL_LAS_CACHE = ParsedLasCache()


def load_las_sheets_cached(source: object, loader: Callable[[object], Mapping[str, pd.DataFrame]]):
    """Load LAS sheets once per exact file content and return defensive copies."""

    return GLOBAL_LAS_CACHE.get_or_load(source, loader)


REVISION_STATE_KEY = "engineering_pipeline_revisions"


def revision_controller_from_state(state: MutableMapping[str, object]) -> RevisionController:
    """Restore a revision controller from serializable session state."""

    raw = state.get(REVISION_STATE_KEY)
    if isinstance(raw, Mapping):
        snapshot = RevisionSnapshot(
            data=int(raw.get("data", 0)),
            calculation=int(raw.get("calculation", 0)),
            presentation=int(raw.get("presentation", 0)),
            export=int(raw.get("export", 0)),
        )
    else:
        snapshot = RevisionSnapshot()
    return RevisionController(snapshot)


def persist_revisions(state: MutableMapping[str, object], snapshot: RevisionSnapshot) -> None:
    state[REVISION_STATE_KEY] = {
        "data": snapshot.data,
        "calculation": snapshot.calculation,
        "presentation": snapshot.presentation,
        "export": snapshot.export,
    }

APPLIED_MAPPING_STATE_KEY = "engineering_applied_mapping"


@dataclass(frozen=True, slots=True)
class AppliedMappingState:
    """Validated mapping snapshot separated from mutable Streamlit widgets."""

    source_signature: str
    sheet_name: str
    header_row: int
    mapping: Mapping[str, str]
    ch_mode: str


def persist_applied_mapping(
    state: MutableMapping[str, object],
    applied: AppliedMappingState,
) -> None:
    """Persist a JSON-safe applied mapping snapshot in session state."""

    state[APPLIED_MAPPING_STATE_KEY] = {
        "source_signature": applied.source_signature,
        "sheet_name": applied.sheet_name,
        "header_row": int(applied.header_row),
        "mapping": {str(key): str(value) for key, value in applied.mapping.items()},
        "ch_mode": applied.ch_mode,
    }


def applied_mapping_from_state(
    state: MutableMapping[str, object],
) -> AppliedMappingState | None:
    """Restore an applied mapping snapshot, ignoring malformed legacy state."""

    raw = state.get(APPLIED_MAPPING_STATE_KEY)
    if not isinstance(raw, Mapping):
        return None
    mapping = raw.get("mapping")
    if not isinstance(mapping, Mapping):
        return None
    source_signature = str(raw.get("source_signature", "")).strip()
    sheet_name = str(raw.get("sheet_name", "")).strip()
    ch_mode = str(raw.get("ch_mode", "A")).strip() or "A"
    if not source_signature or not sheet_name:
        return None
    try:
        header_row = int(raw.get("header_row", 0))
    except (TypeError, ValueError):
        return None
    return AppliedMappingState(
        source_signature=source_signature,
        sheet_name=sheet_name,
        header_row=header_row,
        mapping={str(key): str(value) for key, value in mapping.items()},
        ch_mode=ch_mode,
    )


def mapping_matches_source(applied: AppliedMappingState | None, source_signature: str) -> bool:
    """Return True only when the applied mapping belongs to current prepared data."""

    return applied is not None and applied.source_signature == source_signature


APPLIED_PRESENTATION_STATE_KEY = "engineering_applied_presentation"


@dataclass(frozen=True, slots=True)
class AppliedPresentationState:
    """Immutable presentation snapshot separated from mutable UI widgets."""

    source_signature: str
    calculation_revision: int
    settings: Mapping[str, object]


def persist_applied_presentation(
    state: MutableMapping[str, object],
    applied: AppliedPresentationState,
) -> None:
    """Persist a JSON-safe presentation snapshot in session state."""

    state[APPLIED_PRESENTATION_STATE_KEY] = {
        "source_signature": str(applied.source_signature),
        "calculation_revision": int(applied.calculation_revision),
        "settings": dict(applied.settings),
    }


def applied_presentation_from_state(
    state: MutableMapping[str, object],
) -> AppliedPresentationState | None:
    """Restore an applied presentation snapshot and reject malformed state."""

    raw = state.get(APPLIED_PRESENTATION_STATE_KEY)
    if not isinstance(raw, Mapping):
        return None
    settings = raw.get("settings")
    if not isinstance(settings, Mapping):
        return None
    source_signature = str(raw.get("source_signature", "")).strip()
    if not source_signature:
        return None
    try:
        calculation_revision = int(raw.get("calculation_revision", -1))
    except (TypeError, ValueError):
        return None
    if calculation_revision < 0:
        return None
    return AppliedPresentationState(
        source_signature=source_signature,
        calculation_revision=calculation_revision,
        settings=dict(settings),
    )


def presentation_matches_source(
    applied: AppliedPresentationState | None,
    source_signature: str,
    calculation_revision: int,
) -> bool:
    """Return True only for the exact calculated dataset revision."""

    return (
        applied is not None
        and applied.source_signature == source_signature
        and applied.calculation_revision == int(calculation_revision)
    )


APPLIED_CORRELATION_STATE_KEY = "engineering_applied_correlation"


@dataclass(frozen=True, slots=True)
class AppliedCorrelationState:
    """Immutable correlation snapshot separated from mutable LAS workspace widgets."""

    source_signature: str
    settings: Mapping[str, object]
    studio_settings: Mapping[str, object] = field(default_factory=dict)


def persist_applied_correlation(
    state: MutableMapping[str, object],
    applied: AppliedCorrelationState,
) -> None:
    """Persist a JSON-safe correlation presentation snapshot."""

    state[APPLIED_CORRELATION_STATE_KEY] = {
        "source_signature": str(applied.source_signature),
        "settings": dict(applied.settings),
        "studio_settings": dict(applied.studio_settings),
    }


def applied_correlation_from_state(
    state: MutableMapping[str, object],
) -> AppliedCorrelationState | None:
    """Restore an applied correlation snapshot and reject malformed state."""

    raw = state.get(APPLIED_CORRELATION_STATE_KEY)
    if not isinstance(raw, Mapping):
        return None
    settings = raw.get("settings")
    studio_settings = raw.get("studio_settings", {})
    source_signature = str(raw.get("source_signature", "")).strip()
    if not source_signature or not isinstance(settings, Mapping) or not isinstance(studio_settings, Mapping):
        return None
    return AppliedCorrelationState(
        source_signature=source_signature,
        settings=dict(settings),
        studio_settings=dict(studio_settings),
    )


def correlation_matches_source(
    applied: AppliedCorrelationState | None,
    source_signature: str,
) -> bool:
    """Return True only when correlation settings belong to current LAS contents."""

    return applied is not None and applied.source_signature == source_signature


APPLIED_EXPORT_STATE_KEY = "engineering_applied_export"


@dataclass(frozen=True, slots=True)
class AppliedExportState:
    """Immutable export request bound to an exact presentation revision."""

    source_signature: str
    presentation_revision: int
    settings: Mapping[str, object]


def persist_applied_export(
    state: MutableMapping[str, object],
    applied: AppliedExportState,
) -> None:
    """Persist a JSON-safe export request snapshot."""

    state[APPLIED_EXPORT_STATE_KEY] = {
        "source_signature": str(applied.source_signature),
        "presentation_revision": int(applied.presentation_revision),
        "settings": dict(applied.settings),
    }


def applied_export_from_state(
    state: MutableMapping[str, object],
) -> AppliedExportState | None:
    """Restore an applied export request and reject malformed legacy state."""

    raw = state.get(APPLIED_EXPORT_STATE_KEY)
    if not isinstance(raw, Mapping):
        return None
    settings = raw.get("settings")
    source_signature = str(raw.get("source_signature", "")).strip()
    if not source_signature or not isinstance(settings, Mapping):
        return None
    try:
        presentation_revision = int(raw.get("presentation_revision", -1))
    except (TypeError, ValueError):
        return None
    if presentation_revision < 0:
        return None
    return AppliedExportState(
        source_signature=source_signature,
        presentation_revision=presentation_revision,
        settings=dict(settings),
    )


def export_matches_source(
    applied: AppliedExportState | None,
    source_signature: str,
    presentation_revision: int,
) -> bool:
    """Return True only for an export created from the current presentation."""

    return (
        applied is not None
        and applied.source_signature == source_signature
        and applied.presentation_revision == int(presentation_revision)
    )
