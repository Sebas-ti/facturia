"""Blob Storage client for the `ingest` node (docs/spec.md §2.1).
Azurite locally, real Azure Blob Storage in prod — same connection-string
interface, see app.config.settings.azure_storage_connection_string."""

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient

from app.config import settings

CONTAINER_NAME = "invoices"


class BlobStorageClient:
    def __init__(self) -> None:
        self._service = BlobServiceClient.from_connection_string(
            settings.azure_storage_connection_string
        )

    def upload_invoice_pdf(self, file_hash: str, pdf_bytes: bytes) -> str:
        container_client = self._service.get_container_client(CONTAINER_NAME)
        try:
            container_client.create_container()
        except ResourceExistsError:
            pass

        blob_client = container_client.get_blob_client(f"{file_hash}.pdf")
        blob_client.upload_blob(pdf_bytes, overwrite=True)
        return blob_client.url
