"""PDF text extraction with a graceful dependency ladder.

Primary path uses ``pdfplumber`` (pdfminer.six under the hood), which produces
well-ordered text for most jamabandi layouts. When it is not installed, or it
yields nothing useful (some government PDFs use custom glyph encodings), we fall
back to the pure-stdlib extractor in :mod:`jamabandi.stdlib_pdf`.
"""
from __future__ import annotations

from typing import Tuple

from . import stdlib_pdf


def _extract_pdfplumber(pdf_bytes: bytes) -> str:
    import io

    import pdfplumber  # type: ignore

    chunks = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            if txt:
                chunks.append(txt)
    return "\n".join(chunks)


def extract_text_verbose(pdf_bytes: bytes) -> Tuple[str, str]:
    """Return ``(text, method)`` where method is 'pdfplumber' or 'stdlib'."""
    text = ""
    try:
        text = _extract_pdfplumber(pdf_bytes)
        if text and len(text.strip()) > 40:
            return text, "pdfplumber"
    except ImportError:
        pass
    except Exception:
        # any pdfplumber parse error -> fall through to stdlib
        pass

    fallback = stdlib_pdf.extract_text(pdf_bytes)
    # Prefer whichever recovered more content.
    if len(fallback.strip()) >= len(text.strip()):
        return fallback, "stdlib"
    return text, "pdfplumber"


def extract_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes, best available method."""
    return extract_text_verbose(pdf_bytes)[0]
