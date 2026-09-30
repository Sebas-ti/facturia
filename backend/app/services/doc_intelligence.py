"""Client for Azure AI Document Intelligence's prebuilt-invoice model.

See docs/spec.md §2.1. The real client (Azure SDK) lands in a later task
once Azure credentials are available (PROGRESS.md 2.7); for now only the
Protocol and a fixture-backed mock exist, per AGENTS.md rule 6.
"""

import hashlib
from typing import Protocol

from app.schemas.extraction import RawInvoiceExtraction


class DocumentIntelligenceClient(Protocol):
    def extract_invoice(self, pdf_bytes: bytes) -> RawInvoiceExtraction: ...


class FixtureDocumentIntelligenceClient:
    """Returns pre-recorded RawInvoiceExtraction fixtures, keyed by the
    SHA-256 of the PDF bytes (matches `ingest`'s file_hash, see spec §2.1)."""

    def __init__(self, fixtures: dict[str, RawInvoiceExtraction]) -> None:
        self._fixtures = fixtures

    def extract_invoice(self, pdf_bytes: bytes) -> RawInvoiceExtraction:
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        try:
            return self._fixtures[file_hash]
        except KeyError:
            raise KeyError(f"No fixture registered for file_hash {file_hash!r}") from None
