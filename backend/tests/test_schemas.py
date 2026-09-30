import json
from pathlib import Path
from typing import Any

import pytest

from app.schemas import ExtractedInvoice

GROUND_TRUTH_PATH = Path(__file__).parents[2] / "data" / "ground_truth.json"


def _map_line(linea: dict[str, Any]) -> dict[str, Any]:
    return {
        "sku": linea["sku"],
        "description": linea["descripcion"],
        "quantity": linea["cantidad"],
        "unit_price": linea["precio_unitario"],
        "vat_rate": linea["iva_pct"],
        "line_subtotal": linea["subtotal"],
    }


def _map_bank_account(cuenta: dict[str, Any] | None) -> dict[str, Any] | None:
    if cuenta is None:
        return None
    return {
        "bank": cuenta["banco"],
        "account_type": cuenta["tipo"],
        "number": cuenta["numero"],
    }


def _map_extracted_invoice(esperado: dict[str, Any]) -> dict[str, Any]:
    return {
        "supplier_nit": esperado["proveedor_nit"],
        "supplier_dv": esperado["proveedor_dv_impreso"],
        "supplier_name": esperado["proveedor_razon_social"],
        "invoice_number": esperado["numero_factura"],
        "issue_date": esperado["fecha_emision"],
        "due_date": esperado["fecha_vencimiento"],
        "purchase_order": esperado["orden_compra"],
        "currency": esperado["moneda"],
        "lines": [_map_line(linea) for linea in esperado["lineas"]],
        "subtotal": esperado["subtotal"],
        "vat_total": esperado["iva"],
        "total": esperado["total"],
        "cufe": esperado["cufe"],
        "bank_account": _map_bank_account(esperado["cuenta_bancaria"]),
    }


def _load_ground_truth_invoices() -> list[dict[str, Any]]:
    data = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    return data["facturas"]


@pytest.mark.parametrize(
    "factura", _load_ground_truth_invoices(), ids=lambda factura: factura["id"]
)
def test_ground_truth_esperado_validates_as_extracted_invoice(
    factura: dict[str, Any],
) -> None:
    mapped = _map_extracted_invoice(factura["esperado"])
    invoice = ExtractedInvoice(**mapped)
    assert invoice.invoice_number == factura["esperado"]["numero_factura"]
