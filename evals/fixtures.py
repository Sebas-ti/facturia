"""Synthetic raw-extraction fixtures for the 15 sample invoices (--mock mode).

No real Azure Document Intelligence calls happen here — AGENTS.md rule 6.
These fixtures re-encode data/ground_truth.json's expected values back into
the raw, pre-normalization text each PDF layout (A/B/C, scripts/generate_data.py)
actually renders, so app.agents.extract + app.services.normalize have real
normalization work to do instead of a trivial passthrough.
"""

from typing import Any

from app.schemas.extraction import RawField, RawInvoiceExtraction, RawInvoiceLine

# (layout, prefijo) per supplier NIT — from scripts/generate_data.py PROVEEDORES/DESCONOCIDO.
LAYOUT_BY_NIT = {
    "900482113": ("A", "FEPC"),
    "901117654": ("B", "TRS"),
    "800273946": ("C", "LTV"),
    "901338820": ("A", "CMA"),
    "900915402": ("B", "TSE"),
    "901604587": ("C", "MND"),
    "901777045": ("A", "SRX"),
}

DEFAULT_CONFIDENCE = 0.95
SCANNED_CONFIDENCE = 0.70  # F15 is a noisy scan; see data/README.md

# No-OC placeholder text per layout (scripts/generate_data.py draw()).
_NO_PO_TEXT = {"A": "—", "B": "—", "C": "N/A"}


def _cop(value: float) -> str:
    """Mirrors scripts/generate_data.py's cop(): Colombian amount format."""
    return "$ " + f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _raw_invoice_number(prefijo: str, numero: str, layout: str) -> str:
    if layout == "A":
        return f"{prefijo} {numero}"
    if layout == "B":
        return f"No. {prefijo}-{numero}"
    return f"{prefijo}{numero}"


def _raw_nit(nit: str, dv: int, layout: str) -> str:
    return f"{nit} - {dv}" if layout == "C" else f"{nit}-{dv}"


def build_raw_extraction(factura: dict[str, Any]) -> RawInvoiceExtraction:
    esperado = factura["esperado"]
    nit = esperado["proveedor_nit"]
    layout, prefijo = LAYOUT_BY_NIT[nit]
    numero = esperado["numero_factura"].removeprefix(f"{prefijo}-")
    confidence = SCANNED_CONFIDENCE if factura["id"] == "F15" else DEFAULT_CONFIDENCE

    def field(value: str | None) -> RawField:
        return RawField(value=value, confidence=confidence)

    cuenta = esperado["cuenta_bancaria"]
    bank_line = (
        f"Consignar a: {cuenta['banco']} · Cuenta {cuenta['tipo']} No. {cuenta['numero']} · "
        f"Titular: {esperado['proveedor_razon_social']}"
    )
    cufe = esperado["cufe"]
    full_text = f"{bank_line}\nCUFE:\n{cufe[:64]}\n{cufe[64:]}\n"

    orden_compra = esperado["orden_compra"]
    raw_po = orden_compra if orden_compra else _NO_PO_TEXT[layout]

    lines = [
        RawInvoiceLine(
            sku=field(linea["sku"] or "-"),
            description=field(linea["descripcion"]),
            quantity=field(str(linea["cantidad"])),
            unit_price=field(_cop(linea["precio_unitario"])),
            vat_rate=field(f"{linea['iva_pct']}%"),
            line_subtotal=field(_cop(linea["subtotal"])),
        )
        for linea in esperado["lineas"]
    ]

    return RawInvoiceExtraction(
        supplier_nit=field(_raw_nit(nit, esperado["proveedor_dv_impreso"], layout)),
        supplier_name=field(esperado["proveedor_razon_social"]),
        invoice_number=field(_raw_invoice_number(prefijo, numero, layout)),
        issue_date=field(esperado["fecha_emision"]),
        due_date=field(esperado["fecha_vencimiento"]),
        purchase_order=field(raw_po),
        subtotal=field(_cop(esperado["subtotal"])),
        vat_total=field(_cop(esperado["iva"])),
        total=field(_cop(esperado["total"])),
        lines=lines,
        full_text=full_text,
    )
