from decimal import Decimal

from app.schemas.finding import Finding, FindingCode
from app.schemas.invoice import ExtractedInvoice
from app.schemas.purchase_order import PurchaseOrder

PRICE_TOLERANCE_PCT = Decimal(2)


def check_matching(
    invoice: ExtractedInvoice,
    purchase_orders: dict[str, PurchaseOrder],
    received_quantity: dict[tuple[str, str], Decimal],
    previously_invoiced_quantity: dict[tuple[str, str], Decimal] | None = None,
) -> list[Finding]:
    po = purchase_orders.get(invoice.purchase_order) if invoice.purchase_order else None
    if po is None:
        return [
            Finding(
                code=FindingCode.MISSING_PO,
                severity="MEDIA",
                message="La factura no referencia una orden de compra válida.",
                evidence={"orden_compra": invoice.purchase_order},
            )
        ]

    previously_invoiced_quantity = previously_invoiced_quantity or {}
    po_lines_by_sku = {line.sku: line for line in po.lines}
    findings: list[Finding] = []

    for line in invoice.lines:
        if line.sku is None or line.sku not in po_lines_by_sku:
            continue
        po_line = po_lines_by_sku[line.sku]

        if po_line.unit_price == 0:
            price_diff_pct = Decimal(0) if line.unit_price == 0 else Decimal(100)
        else:
            price_diff_pct = abs(line.unit_price - po_line.unit_price) / po_line.unit_price * 100
        if price_diff_pct > PRICE_TOLERANCE_PCT:
            findings.append(
                Finding(
                    code=FindingCode.PRICE_MISMATCH,
                    severity="MEDIA",
                    message=(
                        f"El precio unitario de {line.sku} difiere más de "
                        f"{PRICE_TOLERANCE_PCT}% del de la OC {po.number}."
                    ),
                    evidence={
                        "sku": line.sku,
                        "precio_oc": str(po_line.unit_price),
                        "precio_factura": str(line.unit_price),
                        "diferencia_pct": str(price_diff_pct),
                    },
                )
            )

        key = (po.number, line.sku)
        accumulated = previously_invoiced_quantity.get(key, Decimal(0)) + line.quantity
        received = received_quantity.get(key, Decimal(0))
        if accumulated > received:
            findings.append(
                Finding(
                    code=FindingCode.QTY_EXCEEDS_RECEIPT,
                    severity="MEDIA",
                    message=(
                        f"La cantidad facturada acumulada de {line.sku} "
                        f"supera lo recibido en almacén."
                    ),
                    evidence={
                        "sku": line.sku,
                        "cantidad_facturada_acumulada": str(accumulated),
                        "cantidad_recibida": str(received),
                    },
                )
            )

    return findings
