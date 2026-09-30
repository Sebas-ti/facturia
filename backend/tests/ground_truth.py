import json
from pathlib import Path
from typing import Any

from app.schemas import ExtractedInvoice

GROUND_TRUTH_PATH = Path(__file__).parents[2] / "data" / "ground_truth.json"


def load_ground_truth() -> dict[str, Any]:
    return json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))


def load_facturas() -> list[dict[str, Any]]:
    return load_ground_truth()["facturas"]


def get_factura(factura_id: str) -> dict[str, Any]:
    for factura in load_facturas():
        if factura["id"] == factura_id:
            return factura
    raise KeyError(f"No factura with id {factura_id!r} in ground_truth.json")


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


def map_extracted_invoice(esperado: dict[str, Any]) -> dict[str, Any]:
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


def extracted_invoice(factura_id: str) -> ExtractedInvoice:
    factura = get_factura(factura_id)
    return ExtractedInvoice(**map_extracted_invoice(factura["esperado"]))
