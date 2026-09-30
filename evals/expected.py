"""Builds the expected `ExtractedInvoice` straight from data/ground_truth.json,
the oracle evals compares the pipeline's output against (docs/spec.md §9)."""

from typing import Any

from app.schemas.invoice import ExtractedInvoice


def _line(linea: dict[str, Any]) -> dict[str, Any]:
    return {
        "sku": linea["sku"],
        "description": linea["descripcion"],
        "quantity": linea["cantidad"],
        "unit_price": linea["precio_unitario"],
        "vat_rate": linea["iva_pct"],
        "line_subtotal": linea["subtotal"],
    }


def _bank_account(cuenta: dict[str, Any] | None) -> dict[str, Any] | None:
    if cuenta is None:
        return None
    return {"bank": cuenta["banco"], "account_type": cuenta["tipo"], "number": cuenta["numero"]}


def expected_invoice(factura: dict[str, Any]) -> ExtractedInvoice:
    esperado = factura["esperado"]
    return ExtractedInvoice(
        supplier_nit=esperado["proveedor_nit"],
        supplier_dv=esperado["proveedor_dv_impreso"],
        supplier_name=esperado["proveedor_razon_social"],
        invoice_number=esperado["numero_factura"],
        issue_date=esperado["fecha_emision"],
        due_date=esperado["fecha_vencimiento"],
        purchase_order=esperado["orden_compra"],
        currency=esperado["moneda"],
        lines=[_line(linea) for linea in esperado["lineas"]],
        subtotal=esperado["subtotal"],
        vat_total=esperado["iva"],
        total=esperado["total"],
        cufe=esperado["cufe"],
        bank_account=_bank_account(esperado["cuenta_bancaria"]),
    )
