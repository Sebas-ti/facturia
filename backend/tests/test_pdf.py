from io import BytesIO
from pathlib import Path

from pypdf import PdfWriter

from app.services.pdf import compute_file_hash, detect_is_scanned

DATA_DIR = Path(__file__).parents[2] / "data"


def test_compute_file_hash_is_sha256_hex() -> None:
    file_hash = compute_file_hash(b"hello")
    assert file_hash == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_compute_file_hash_differs_for_different_bytes() -> None:
    assert compute_file_hash(b"a") != compute_file_hash(b"b")


def test_detect_is_scanned_false_for_native_pdf_with_text() -> None:
    pdf_bytes = (DATA_DIR / "facturas" / "F01_FEPC-1045.pdf").read_bytes()
    assert detect_is_scanned(pdf_bytes) is False


def test_detect_is_scanned_true_for_the_noisy_scanned_invoice() -> None:
    """F15 is rendered from an image with no text layer at all, see
    data/README.md and scripts/generate_data.py."""
    pdf_bytes = (DATA_DIR / "facturas" / "F15_CMA-3355.pdf").read_bytes()
    assert detect_is_scanned(pdf_bytes) is True


def test_detect_is_scanned_true_for_an_empty_pdf() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)

    assert detect_is_scanned(buffer.getvalue()) is True
