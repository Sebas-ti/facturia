"""`ingest` node (docs/spec.md §2.1): hashes the PDF, detects whether it's a
scanned/image-only document, and saves it to Blob Storage."""

from dataclasses import dataclass

from app.services.blob import BlobStorageClient
from app.services.pdf import compute_file_hash, detect_is_scanned


@dataclass
class IngestResult:
    file_hash: str
    is_scanned: bool
    blob_url: str


def ingest(pdf_bytes: bytes, blob_client: BlobStorageClient) -> IngestResult:
    file_hash = compute_file_hash(pdf_bytes)
    is_scanned = detect_is_scanned(pdf_bytes)
    blob_url = blob_client.upload_invoice_pdf(file_hash, pdf_bytes)
    return IngestResult(file_hash=file_hash, is_scanned=is_scanned, blob_url=blob_url)
