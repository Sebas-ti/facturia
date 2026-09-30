from pathlib import Path

from app.agents.ingest import ingest
from app.services.blob import BlobStorageClient
from app.services.pdf import compute_file_hash

DATA_DIR = Path(__file__).parents[3] / "data"


def test_ingest_native_pdf() -> None:
    """Requires `docker compose up -d azurite` (see AGENTS.md)."""
    pdf_bytes = (DATA_DIR / "facturas" / "F01_FEPC-1045.pdf").read_bytes()

    result = ingest(pdf_bytes, BlobStorageClient())

    assert result.file_hash == compute_file_hash(pdf_bytes)
    assert result.is_scanned is False
    assert result.file_hash in result.blob_url


def test_ingest_scanned_pdf() -> None:
    pdf_bytes = (DATA_DIR / "facturas" / "F15_CMA-3355.pdf").read_bytes()

    result = ingest(pdf_bytes, BlobStorageClient())

    assert result.is_scanned is True
