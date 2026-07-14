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
from typing import Iterable


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
class PdfPreviewPageJumpValidation:
    requested_page: int
    normalized_page: int
    adjusted: bool
    code: str
    message: str


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





def resolve_pdf_preview_cache(
    payload: object,
    *,
    signature: str,
) -> PdfPreviewResult | None:
    """Return a cached preview result for ``signature`` from a bounded cache payload.

    The helper accepts both the legacy single-entry structure and the newer
    multi-entry structure so existing Streamlit session state remains valid
    after an application update.
    """

    if not isinstance(payload, dict) or not signature:
        return None
    if payload.get("signature") == signature and isinstance(payload.get("result"), PdfPreviewResult):
        return payload["result"]
    entries = payload.get("entries")
    if not isinstance(entries, (list, tuple)):
        return None
    for entry in entries:
        if (
            isinstance(entry, dict)
            and entry.get("signature") == signature
            and isinstance(entry.get("result"), PdfPreviewResult)
        ):
            return entry["result"]
    return None


def store_pdf_preview_cache(
    payload: object,
    *,
    signature: str,
    result: PdfPreviewResult,
    max_entries: int = 3,
) -> dict[str, object]:
    """Store a preview in a small newest-first cache suitable for Session State."""

    try:
        safe_max_entries = max(1, min(int(max_entries), 6))
    except (TypeError, ValueError):
        safe_max_entries = 3

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
    return {"entries": entries[:safe_max_entries]}


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
    "PdfPreviewPage",
    "PdfPreviewPageJumpValidation",
    "PdfPreviewResult",
    "PdfPreviewUnavailableError",
    "build_pdf_preview",
    "build_pdf_preview_signature",
    "next_pdf_preview_start_page",
    "resolve_pdf_preview_cache",
    "store_pdf_preview_cache",
    "bounded_pdf_preview_start_page",
    "shift_pdf_preview_window",
    "validate_pdf_preview_page_jump",
]
