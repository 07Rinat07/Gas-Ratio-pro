from __future__ import annotations

"""Safe, bounded raster previews for already-rendered PDF artifacts."""

from dataclasses import dataclass, replace
from io import BytesIO
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
from time import perf_counter
from typing import Any, Iterable


@dataclass(frozen=True)
class PdfPreviewPage:
    page_number: int
    image_png: bytes
    width: int
    height: int


@dataclass(frozen=True)
class PdfPreviewResult:
    pages: tuple[PdfPreviewPage, ...]
    total_pages: int
    rendered_pages: int
    backend: str
    truncated: bool
    render_duration_seconds: float = 0.0
    source_size_bytes: int = 0
    image_size_bytes: int = 0

    @property
    def average_page_size_bytes(self) -> int:
        if self.rendered_pages <= 0:
            return 0
        return int(round(self.image_size_bytes / self.rendered_pages))


@dataclass(frozen=True)
class PdfPreviewCacheLookup:
    result: PdfPreviewResult | None
    hit: bool
    source: str
    entry_index: int | None = None


@dataclass(frozen=True)
class PdfPreviewCacheStats:
    entry_count: int = 0
    rendered_pages: int = 0
    image_size_bytes: int = 0
    largest_entry_bytes: int = 0
    status: str = "empty"
    warning_threshold_bytes: int = 8 * 1024 * 1024
    critical_threshold_bytes: int = 24 * 1024 * 1024

    @property
    def average_entry_bytes(self) -> int:
        if self.entry_count <= 0:
            return 0
        return int(round(self.image_size_bytes / self.entry_count))

    @property
    def pressure_ratio(self) -> float:
        if self.critical_threshold_bytes <= 0:
            return 0.0
        return max(0.0, self.image_size_bytes / self.critical_threshold_bytes)


@dataclass(frozen=True)
class PdfPreviewCacheStoreResult:
    payload: dict[str, object]
    evicted_signatures: tuple[str, ...] = ()
    evicted_bytes: int = 0
    retained_bytes: int = 0
    budget_bytes: int = 0

    @property
    def eviction_count(self) -> int:
        return len(self.evicted_signatures)


@dataclass(frozen=True)
class PdfPreviewPageJumpValidation:
    requested_page: int
    normalized_page: int
    adjusted: bool
    code: str
    message: str




@dataclass(frozen=True)
class PdfPreviewRuntimeCacheSnapshot:
    entry_count: int
    rendered_pages: int
    image_size_bytes: int
    max_entries: int
    max_bytes: int
    hits: int
    misses: int
    invalidations: int
    evictions: int

    @property
    def measured(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        return round((self.hits / self.measured) * 100.0, 2) if self.measured else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_count": self.entry_count,
            "rendered_pages": self.rendered_pages,
            "image_size_bytes": self.image_size_bytes,
            "max_entries": self.max_entries,
            "max_bytes": self.max_bytes,
            "hits": self.hits,
            "misses": self.misses,
            "invalidations": self.invalidations,
            "evictions": self.evictions,
            "measured": self.measured,
            "hit_rate": self.hit_rate,
        }


class PdfPreviewRuntimeCache:
    """Process-local bounded cache for heavy PDF preview PNG payloads.

    The cache deliberately lives behind ``RuntimeServiceRegistry`` instead of
    serializable Session State. Only :meth:`snapshot` crosses the diagnostic
    boundary. ``metrics`` is an optional ``CacheMetricCounter``-compatible
    object, kept duck-typed to avoid coupling reports to the core package.
    """

    def __init__(
        self,
        *,
        max_entries: int = 3,
        max_bytes: int = 24 * 1024 * 1024,
        metrics: object | None = None,
    ) -> None:
        self.max_entries = max(1, min(int(max_entries), 6))
        self.max_bytes = max(1, min(int(max_bytes), 128 * 1024 * 1024))
        self._payload: dict[str, object] = {"entries": []}
        self._metrics = metrics
        self._hits = 0
        self._misses = 0
        self._invalidations = 0
        self._evictions = 0
        self._sync_metric_entries()

    def _metric_call(self, name: str, *args: object) -> None:
        method = getattr(self._metrics, name, None)
        if callable(method):
            method(*args)

    def _sync_metric_entries(self) -> None:
        stats = summarize_pdf_preview_cache(self._payload)
        self._metric_call("set_entries", stats.entry_count)

    def configure(self, *, max_entries: int | None = None, max_bytes: int | None = None) -> None:
        if max_entries is not None:
            self.max_entries = max(1, min(int(max_entries), 6))
        if max_bytes is not None:
            self.max_bytes = max(1, min(int(max_bytes), 128 * 1024 * 1024))
        # Re-apply budgets without requiring a new rendered result.
        entries = self._payload.get("entries")
        if not isinstance(entries, list):
            entries = []
        evicted = 0
        while len(entries) > self.max_entries:
            entries.pop()
            evicted += 1
        def size(entry: object) -> int:
            if not isinstance(entry, dict):
                return 0
            result = entry.get("result")
            return max(0, int(result.image_size_bytes)) if isinstance(result, PdfPreviewResult) else 0
        retained = sum(size(entry) for entry in entries)
        while len(entries) > 1 and retained > self.max_bytes:
            retained -= size(entries.pop())
            evicted += 1
        self._payload = {"entries": entries}
        if evicted:
            self._evictions += evicted
            self._metric_call("evict", evicted)
        self._sync_metric_entries()

    def inspect(self, signature: str) -> PdfPreviewCacheLookup:
        lookup = inspect_pdf_preview_cache(self._payload, signature=signature)
        if lookup.hit:
            self._hits += 1
            self._metric_call("hit")
            # Promote a hit to MRU without copying PNG payloads.
            entries = self._payload.get("entries")
            if isinstance(entries, list) and lookup.entry_index not in (None, 0):
                entry = entries.pop(int(lookup.entry_index))
                entries.insert(0, entry)
        else:
            self._misses += 1
            self._metric_call("miss")
        return lookup

    def store(self, signature: str, result: PdfPreviewResult) -> PdfPreviewCacheStoreResult:
        stored = store_pdf_preview_cache_with_diagnostics(
            self._payload,
            signature=signature,
            result=result,
            max_entries=self.max_entries,
            max_bytes=self.max_bytes,
        )
        self._payload = stored.payload
        if stored.eviction_count:
            self._evictions += stored.eviction_count
            self._metric_call("evict", stored.eviction_count)
        self._sync_metric_entries()
        return stored

    def clear(self) -> int:
        count = summarize_pdf_preview_cache(self._payload).entry_count
        self._payload = {"entries": []}
        self._invalidations += 1
        self._metric_call("invalidate")
        self._sync_metric_entries()
        return count

    def close(self) -> None:
        self.clear()

    def known_total_pages(self) -> int:
        entries = self._payload.get("entries")
        if not isinstance(entries, (list, tuple)):
            return 0
        return max(
            (
                int(entry["result"].total_pages)
                for entry in entries
                if isinstance(entry, dict)
                and isinstance(entry.get("result"), PdfPreviewResult)
                and int(entry["result"].total_pages) > 0
            ),
            default=0,
        )

    def stats(
        self,
        *,
        warning_threshold_bytes: int | None = None,
        critical_threshold_bytes: int | None = None,
    ) -> PdfPreviewCacheStats:
        warning = (
            max(1, int(warning_threshold_bytes))
            if warning_threshold_bytes is not None
            else max(1, int(self.max_bytes * 0.75))
        )
        critical = (
            max(warning, int(critical_threshold_bytes))
            if critical_threshold_bytes is not None
            else self.max_bytes
        )
        return summarize_pdf_preview_cache(
            self._payload,
            warning_threshold_bytes=warning,
            critical_threshold_bytes=critical,
        )

    def snapshot(self) -> PdfPreviewRuntimeCacheSnapshot:
        stats = self.stats()
        return PdfPreviewRuntimeCacheSnapshot(
            entry_count=stats.entry_count,
            rendered_pages=stats.rendered_pages,
            image_size_bytes=stats.image_size_bytes,
            max_entries=self.max_entries,
            max_bytes=self.max_bytes,
            hits=self._hits,
            misses=self._misses,
            invalidations=self._invalidations,
            evictions=self._evictions,
        )


class PdfPreviewUnavailableError(RuntimeError):
    """Raised when no supported local PDF rasterizer is available."""


def _bounded_page_limit(value: int, *, maximum: int = 12) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 5
    return max(1, min(number, maximum))



def _bounded_start_page(value: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 1
    return max(1, number)




def bounded_pdf_preview_start_page(
    value: int,
    *,
    total_pages: int = 0,
    page_limit: int = 5,
) -> int:
    """Normalize a preview start page to a valid bounded window.

    When the exact page count is known, the start page is clamped so the
    selected window never begins past the last useful page group.  For an
    unknown page count, only the lower bound is enforced.
    """

    safe_start = _bounded_start_page(value)
    safe_limit = _bounded_page_limit(page_limit)
    try:
        known_total = max(0, int(total_pages))
    except (TypeError, ValueError):
        known_total = 0
    if known_total <= 0:
        return safe_start
    last_window_start = max(1, ((known_total - 1) // safe_limit) * safe_limit + 1)
    return min(safe_start, last_window_start)




def validate_pdf_preview_page_jump(
    value: int,
    *,
    total_pages: int = 0,
    page_limit: int = 5,
) -> PdfPreviewPageJumpValidation:
    """Validate a direct page jump and explain any normalization.

    The function is UI-independent and never raises for user-entered values.
    When the exact page count is unknown, only the lower bound is enforced.
    """

    try:
        requested = int(value)
    except (TypeError, ValueError):
        requested = 1
    normalized = bounded_pdf_preview_start_page(
        requested, total_pages=total_pages, page_limit=page_limit
    )
    try:
        known_total = max(0, int(total_pages))
    except (TypeError, ValueError):
        known_total = 0

    if requested < 1:
        return PdfPreviewPageJumpValidation(
            requested_page=requested,
            normalized_page=normalized,
            adjusted=True,
            code="below_minimum",
            message="Номер страницы должен быть не меньше 1; выбран первый диапазон.",
        )
    if known_total > 0 and requested > known_total:
        return PdfPreviewPageJumpValidation(
            requested_page=requested,
            normalized_page=normalized,
            adjusted=True,
            code="past_document_end",
            message=(
                f"В документе {known_total} стр.; показан последний доступный "
                f"диапазон с страницы {normalized}."
            ),
        )
    if normalized != requested:
        return PdfPreviewPageJumpValidation(
            requested_page=requested,
            normalized_page=normalized,
            adjusted=True,
            code="window_clamped",
            message=(
                f"Начальная страница скорректирована до {normalized}, чтобы диапазон "
                "не начинался после последней группы страниц."
            ),
        )
    return PdfPreviewPageJumpValidation(
        requested_page=requested,
        normalized_page=normalized,
        adjusted=False,
        code="valid",
        message=f"Диапазон начинается со страницы {normalized}.",
    )

def shift_pdf_preview_window(
    current_start: int,
    *,
    direction: int,
    page_limit: int = 5,
    total_pages: int = 0,
) -> int:
    """Move a bounded preview window backward or forward by one page group."""

    safe_limit = _bounded_page_limit(page_limit)
    safe_current = bounded_pdf_preview_start_page(
        current_start, total_pages=total_pages, page_limit=safe_limit
    )
    step = -safe_limit if int(direction) < 0 else safe_limit
    return bounded_pdf_preview_start_page(
        safe_current + step, total_pages=total_pages, page_limit=safe_limit
    )

def _bounded_dpi(value: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 110
    return max(72, min(number, 180))


def _render_with_pymupdf(pdf_bytes: bytes, *, start_page: int, page_limit: int, dpi: int) -> PdfPreviewResult:
    try:
        import fitz  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise PdfPreviewUnavailableError("PyMuPDF is not installed") from exc

    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        total_pages = int(document.page_count)
        scale = float(dpi) / 72.0
        matrix = fitz.Matrix(scale, scale)
        pages: list[PdfPreviewPage] = []
        start_index = min(max(start_page - 1, 0), total_pages)
        stop_index = min(total_pages, start_index + page_limit)
        for index in range(start_index, stop_index):
            pixmap = document.load_page(index).get_pixmap(matrix=matrix, alpha=False)
            pages.append(
                PdfPreviewPage(
                    page_number=index + 1,
                    image_png=pixmap.tobytes("png"),
                    width=int(pixmap.width),
                    height=int(pixmap.height),
                )
            )
        return PdfPreviewResult(
            pages=tuple(pages),
            total_pages=total_pages,
            rendered_pages=len(pages),
            backend="pymupdf",
            truncated=start_index > 0 or stop_index < total_pages,
        )
    finally:
        document.close()


def _png_dimensions(payload: bytes) -> tuple[int, int]:
    try:
        from PIL import Image
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise PdfPreviewUnavailableError("Pillow is required for pdftoppm previews") from exc
    with Image.open(BytesIO(payload)) as image:
        return int(image.width), int(image.height)


def _render_with_pdftoppm(pdf_bytes: bytes, *, start_page: int, page_limit: int, dpi: int) -> PdfPreviewResult:
    executable = shutil.which("pdftoppm")
    if not executable:
        raise PdfPreviewUnavailableError("pdftoppm is not available")

    with tempfile.TemporaryDirectory(prefix="gas-ratio-pdf-preview-") as temp_dir:
        root = Path(temp_dir)
        pdf_path = root / "source.pdf"
        output_prefix = root / "page"
        pdf_path.write_bytes(pdf_bytes)
        completed = subprocess.run(
            [
                executable,
                "-png",
                "-r",
                str(dpi),
                "-f",
                str(start_page),
                "-l",
                str(start_page + page_limit - 1),
                str(pdf_path),
                str(output_prefix),
            ],
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout or "pdftoppm failed").strip()
            raise PdfPreviewUnavailableError(message[:500])

        files = sorted(root.glob("page-*.png"))
        pages: list[PdfPreviewPage] = []
        for index, path in enumerate(files, start=start_page):
            payload = path.read_bytes()
            width, height = _png_dimensions(payload)
            pages.append(PdfPreviewPage(index, payload, width, height))

        # pdftoppm does not expose page count in this bounded invocation. The
        # result is conservative: reaching the limit means the document may be
        # longer and the UI can communicate that without parsing PDF internals.
        rendered = len(pages)
        return PdfPreviewResult(
            pages=tuple(pages),
            total_pages=(start_page + rendered - 1) if rendered else 0,
            rendered_pages=rendered,
            backend="pdftoppm",
            truncated=start_page > 1 or rendered >= page_limit,
        )





def inspect_pdf_preview_cache(
    payload: object,
    *,
    signature: str,
) -> PdfPreviewCacheLookup:
    """Inspect a preview cache lookup without mutating the cache payload.

    ``source`` is one of ``legacy``, ``entries`` or ``miss``.  The compact
    result is safe for logging and UI telemetry because it never exposes PDF
    bytes or PNG payloads.
    """

    if not isinstance(payload, dict) or not signature:
        return PdfPreviewCacheLookup(None, False, "miss", None)
    if payload.get("signature") == signature and isinstance(payload.get("result"), PdfPreviewResult):
        return PdfPreviewCacheLookup(payload["result"], True, "legacy", 0)
    entries = payload.get("entries")
    if not isinstance(entries, (list, tuple)):
        return PdfPreviewCacheLookup(None, False, "miss", None)
    for index, entry in enumerate(entries):
        if (
            isinstance(entry, dict)
            and entry.get("signature") == signature
            and isinstance(entry.get("result"), PdfPreviewResult)
        ):
            return PdfPreviewCacheLookup(entry["result"], True, "entries", index)
    return PdfPreviewCacheLookup(None, False, "miss", None)


def summarize_pdf_preview_cache(
    payload: object,
    *,
    warning_threshold_bytes: int = 8 * 1024 * 1024,
    critical_threshold_bytes: int = 24 * 1024 * 1024,
) -> PdfPreviewCacheStats:
    """Return bounded, payload-free memory diagnostics for preview cache.

    Only metadata already present on :class:`PdfPreviewResult` is aggregated.
    PDF bytes and PNG payloads are never copied while calculating the summary.
    """

    try:
        warning = max(1, int(warning_threshold_bytes))
    except (TypeError, ValueError):
        warning = 8 * 1024 * 1024
    try:
        critical = max(warning, int(critical_threshold_bytes))
    except (TypeError, ValueError):
        critical = max(warning, 24 * 1024 * 1024)

    results: list[PdfPreviewResult] = []
    if isinstance(payload, dict):
        legacy = payload.get("result")
        if isinstance(legacy, PdfPreviewResult):
            results.append(legacy)
        entries = payload.get("entries")
        if isinstance(entries, (list, tuple)):
            for entry in entries:
                if isinstance(entry, dict) and isinstance(entry.get("result"), PdfPreviewResult):
                    results.append(entry["result"])

    total_bytes = sum(max(0, int(result.image_size_bytes)) for result in results)
    total_pages = sum(max(0, int(result.rendered_pages)) for result in results)
    largest = max((max(0, int(result.image_size_bytes)) for result in results), default=0)
    if not results:
        status = "empty"
    elif total_bytes >= critical:
        status = "critical"
    elif total_bytes >= warning:
        status = "warning"
    else:
        status = "ok"
    return PdfPreviewCacheStats(
        entry_count=len(results),
        rendered_pages=total_pages,
        image_size_bytes=total_bytes,
        largest_entry_bytes=largest,
        status=status,
        warning_threshold_bytes=warning,
        critical_threshold_bytes=critical,
    )


def resolve_pdf_preview_cache(
    payload: object,
    *,
    signature: str,
) -> PdfPreviewResult | None:
    """Return a cached preview result for ``signature``.

    This compatibility wrapper delegates to :func:`inspect_pdf_preview_cache`.
    """

    return inspect_pdf_preview_cache(payload, signature=signature).result


def store_pdf_preview_cache_with_diagnostics(
    payload: object,
    *,
    signature: str,
    result: PdfPreviewResult,
    max_entries: int = 3,
    max_bytes: int = 24 * 1024 * 1024,
) -> PdfPreviewCacheStoreResult:
    """Store a preview and evict oldest ranges to satisfy count and memory budgets.

    The newest range is always retained, even when it alone exceeds ``max_bytes``.
    This keeps the explicit user action useful while ensuring older previews cannot
    grow Session State without bounds.
    """

    try:
        safe_max_entries = max(1, min(int(max_entries), 6))
    except (TypeError, ValueError):
        safe_max_entries = 3
    try:
        safe_max_bytes = max(1, min(int(max_bytes), 128 * 1024 * 1024))
    except (TypeError, ValueError):
        safe_max_bytes = 24 * 1024 * 1024

    entries: list[dict[str, object]] = []
    if isinstance(payload, dict):
        existing = payload.get("entries")
        if isinstance(existing, (list, tuple)):
            for entry in existing:
                if (
                    isinstance(entry, dict)
                    and isinstance(entry.get("signature"), str)
                    and isinstance(entry.get("result"), PdfPreviewResult)
                    and entry.get("signature") != signature
                ):
                    entries.append({"signature": entry["signature"], "result": entry["result"]})
        elif (
            isinstance(payload.get("signature"), str)
            and isinstance(payload.get("result"), PdfPreviewResult)
            and payload.get("signature") != signature
        ):
            entries.append({"signature": payload["signature"], "result": payload["result"]})

    entries.insert(0, {"signature": str(signature), "result": result})
    evicted: list[dict[str, object]] = []
    while len(entries) > safe_max_entries:
        evicted.append(entries.pop())

    def entry_bytes(entry: dict[str, object]) -> int:
        cached_result = entry.get("result")
        if not isinstance(cached_result, PdfPreviewResult):
            return 0
        return max(0, int(cached_result.image_size_bytes))

    retained_bytes = sum(entry_bytes(entry) for entry in entries)
    while len(entries) > 1 and retained_bytes > safe_max_bytes:
        removed = entries.pop()
        removed_bytes = entry_bytes(removed)
        retained_bytes -= removed_bytes
        evicted.append(removed)

    evicted_signatures = tuple(
        str(entry.get("signature", "")) for entry in evicted if entry.get("signature")
    )
    evicted_bytes = sum(entry_bytes(entry) for entry in evicted)
    return PdfPreviewCacheStoreResult(
        payload={"entries": entries},
        evicted_signatures=evicted_signatures,
        evicted_bytes=evicted_bytes,
        retained_bytes=max(0, retained_bytes),
        budget_bytes=safe_max_bytes,
    )


def store_pdf_preview_cache(
    payload: object,
    *,
    signature: str,
    result: PdfPreviewResult,
    max_entries: int = 3,
    max_bytes: int = 24 * 1024 * 1024,
) -> dict[str, object]:
    """Compatibility wrapper returning only the bounded cache payload."""

    return store_pdf_preview_cache_with_diagnostics(
        payload,
        signature=signature,
        result=result,
        max_entries=max_entries,
        max_bytes=max_bytes,
    ).payload


def next_pdf_preview_start_page(
    current_start: int,
    *,
    total_pages: int,
    page_limit: int = 5,
) -> int | None:
    """Return the next valid bounded page-window start, or ``None`` at the end."""

    try:
        known_total = max(0, int(total_pages))
    except (TypeError, ValueError):
        known_total = 0
    if known_total <= 0:
        return None
    safe_limit = _bounded_page_limit(page_limit)
    safe_current = bounded_pdf_preview_start_page(
        current_start, total_pages=known_total, page_limit=safe_limit
    )
    candidate = safe_current + safe_limit
    if candidate > known_total:
        return None
    return bounded_pdf_preview_start_page(
        candidate, total_pages=known_total, page_limit=safe_limit
    )

def build_pdf_preview_signature(
    pdf_content: bytes | bytearray | memoryview,
    *,
    request_signature: str = "",
    page_limit: int = 5,
    start_page: int = 1,
    dpi: int = 110,
) -> str:
    """Return a stable cache signature for a rendered PDF preview.

    The digest binds the preview to both the actual PDF bytes and the current
    export request.  This prevents stale thumbnails from surviving a report
    rebuild that happens to reuse the same UI controls.
    """

    payload = bytes(pdf_content)
    if not payload.startswith(b"%PDF-"):
        raise ValueError("pdf_content must contain a valid PDF payload")
    safe_limit = _bounded_page_limit(page_limit)
    safe_start = _bounded_start_page(start_page)
    safe_dpi = _bounded_dpi(dpi)
    digest = hashlib.sha256()
    digest.update(payload)
    digest.update(b"\0")
    digest.update(str(request_signature or "").encode("utf-8"))
    digest.update(b"\0")
    digest.update(str(safe_limit).encode("ascii"))
    digest.update(b"\0")
    digest.update(str(safe_start).encode("ascii"))
    digest.update(b"\0")
    digest.update(str(safe_dpi).encode("ascii"))
    return digest.hexdigest()

def build_pdf_preview(
    pdf_content: bytes | bytearray | memoryview,
    *,
    page_limit: int = 5,
    start_page: int = 1,
    dpi: int = 110,
) -> PdfPreviewResult:
    """Rasterize a bounded number of PDF pages entirely in temporary storage.

    PyMuPDF is preferred because it reports the exact page count. A local
    ``pdftoppm`` process is used as a fallback. The source PDF is never written
    into the project ``data`` directory.
    """

    payload = bytes(pdf_content)
    if not payload.startswith(b"%PDF-"):
        raise ValueError("pdf_content must contain a valid PDF payload")

    safe_limit = _bounded_page_limit(page_limit)
    safe_start = _bounded_start_page(start_page)
    safe_dpi = _bounded_dpi(dpi)
    errors: list[str] = []
    started_at = perf_counter()
    for renderer in (_render_with_pymupdf, _render_with_pdftoppm):
        try:
            result = renderer(payload, start_page=safe_start, page_limit=safe_limit, dpi=safe_dpi)
            return replace(
                result,
                render_duration_seconds=max(0.0, perf_counter() - started_at),
                source_size_bytes=len(payload),
                image_size_bytes=sum(len(page.image_png) for page in result.pages),
            )
        except PdfPreviewUnavailableError as exc:
            errors.append(str(exc))
    raise PdfPreviewUnavailableError("; ".join(errors) or "No PDF preview backend is available")


__all__ = [
    "PdfPreviewCacheLookup",
    "PdfPreviewCacheStats",
    "PdfPreviewPage",
    "PdfPreviewPageJumpValidation",
    "PdfPreviewResult",
    "PdfPreviewRuntimeCache",
    "PdfPreviewRuntimeCacheSnapshot",
    "PdfPreviewUnavailableError",
    "build_pdf_preview",
    "build_pdf_preview_signature",
    "inspect_pdf_preview_cache",
    "next_pdf_preview_start_page",
    "resolve_pdf_preview_cache",
    "store_pdf_preview_cache",
    "summarize_pdf_preview_cache",
    "bounded_pdf_preview_start_page",
    "shift_pdf_preview_window",
    "validate_pdf_preview_page_jump",
]
