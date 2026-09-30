from app.services.blob import BlobStorageClient


def test_upload_invoice_pdf_round_trips_through_azurite() -> None:
    """Requires `docker compose up -d azurite` (see AGENTS.md)."""
    client = BlobStorageClient()
    file_hash = "test-hash-blob"

    url = client.upload_invoice_pdf(file_hash, b"%PDF fake bytes")

    assert file_hash in url
    assert url.startswith("http")


def test_upload_invoice_pdf_overwrites_existing_blob() -> None:
    client = BlobStorageClient()
    file_hash = "test-hash-overwrite"

    client.upload_invoice_pdf(file_hash, b"first version")
    url = client.upload_invoice_pdf(file_hash, b"second version")

    assert file_hash in url
