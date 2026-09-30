"""Blob Storage client for the `ingest` node (docs/spec.md §2.1).
Azurite locally, real Azure Blob Storage in prod — same connection-string
interface, see app.config.settings.azure_storage_connection_string."""

from datetime import UTC, datetime, timedelta

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobSasPermissions, BlobServiceClient, generate_blob_sas

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

    def generate_sas_url(self, file_hash: str, expiry_hours: int = 1) -> str:
        blob_name = f"{file_hash}.pdf"
        blob_client = self._service.get_blob_client(CONTAINER_NAME, blob_name)
        account_name = blob_client.account_name
        account_key = getattr(self._service.credential, "account_key", None)
        if not account_name or not account_key:
            return blob_client.url

        sas_token = generate_blob_sas(
            account_name=str(account_name),
            container_name=CONTAINER_NAME,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(UTC) + timedelta(hours=expiry_hours),
        )
        return f"{blob_client.url}?{sas_token}"

    def download_pdf(self, file_hash: str) -> bytes:
        blob_client = self._service.get_blob_client(CONTAINER_NAME, f"{file_hash}.pdf")
        return blob_client.download_blob().readall()
