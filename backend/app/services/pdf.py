"""Pure PDF inspection for the `ingest` node (docs/spec.md §2.1)."""

import hashlib
from io import BytesIO

from pypdf import PdfReader

MIN_CHARS_PER_PAGE = 20


def compute_file_hash(pdf_bytes: bytes) -> str:
    return hashlib.sha256(pdf_bytes).hexdigest()


def detect_is_scanned(pdf_bytes: bytes) -> bool:
    """A scanned/image-only PDF has little to no extractable text layer,
    unlike a native PDF (scripts/generate_data.py renders F15 straight from
    an image, with no text layer at all)."""
    reader = PdfReader(BytesIO(pdf_bytes))
    if not reader.pages:
        return True

    total_chars = sum(len((page.extract_text() or "").strip()) for page in reader.pages)
    avg_chars_per_page = total_chars / len(reader.pages)
    return avg_chars_per_page < MIN_CHARS_PER_PAGE
