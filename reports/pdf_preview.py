from __future__ import annotations

"""Safe, bounded raster previews for already-rendered PDF artifacts."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import shutil
import subprocess
import tempfile
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


class PdfPreviewUnavailableError(RuntimeError):
    """Raised when no supported local PDF rasterizer is available."""


def _bounded_page_limit(value: int, *, maximum: int = 12) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 5
    return max(1, min(number, maximum))


def _bounded_dpi(value: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 110
    return max(72, min(number, 180))


def _render_with_pymupdf(pdf_bytes: bytes, *, page_limit: int, dpi: int) -> PdfPreviewResult:
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
        for index in range(min(total_pages, page_limit)):
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
            truncated=total_pages > len(pages),
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


def _render_with_pdftoppm(pdf_bytes: bytes, *, page_limit: int, dpi: int) -> PdfPreviewResult:
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
                "1",
                "-l",
                str(page_limit),
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
        for index, path in enumerate(files, start=1):
            payload = path.read_bytes()
            width, height = _png_dimensions(payload)
            pages.append(PdfPreviewPage(index, payload, width, height))

        # pdftoppm does not expose page count in this bounded invocation. The
        # result is conservative: reaching the limit means the document may be
        # longer and the UI can communicate that without parsing PDF internals.
        rendered = len(pages)
        return PdfPreviewResult(
            pages=tuple(pages),
            total_pages=rendered,
            rendered_pages=rendered,
            backend="pdftoppm",
            truncated=rendered >= page_limit,
        )


def build_pdf_preview(
    pdf_content: bytes | bytearray | memoryview,
    *,
    page_limit: int = 5,
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
    safe_dpi = _bounded_dpi(dpi)
    errors: list[str] = []
    for renderer in (_render_with_pymupdf, _render_with_pdftoppm):
        try:
            return renderer(payload, page_limit=safe_limit, dpi=safe_dpi)
        except PdfPreviewUnavailableError as exc:
            errors.append(str(exc))
    raise PdfPreviewUnavailableError("; ".join(errors) or "No PDF preview backend is available")


__all__ = [
    "PdfPreviewPage",
    "PdfPreviewResult",
    "PdfPreviewUnavailableError",
    "build_pdf_preview",
]
