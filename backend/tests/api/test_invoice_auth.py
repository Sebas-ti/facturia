"""Tests for the API key auth on POST /api/invoices (docs/spec.md §6)."""

import pytest
from fastapi.testclient import TestClient

import app.api.invoices as invoices_module
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def no_real_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(invoices_module, "_process_invoice", lambda *args, **kwargs: None)


def test_rejects_request_without_api_key() -> None:
    response = client.post(
        "/api/invoices", files={"file": ("factura.pdf", b"%PDF-1.4 fake", "application/pdf")}
    )
    assert response.status_code == 401


def test_rejects_request_with_wrong_api_key() -> None:
    response = client.post(
        "/api/invoices",
        files={"file": ("factura.pdf", b"%PDF-1.4 fake", "application/pdf")},
        headers={"X-API-Key": "not-the-real-key"},
    )
    assert response.status_code == 401


def test_other_invoice_endpoints_do_not_require_api_key() -> None:
    response = client.get("/api/invoices")
    assert response.status_code == 200
