"""`match` node (docs/spec.md §2.1): looks up the PO and conciliates
quantities/prices against Postgres, delegating the actual comparison to the
pure app.rules.matching.check_matching."""

import uuid

from sqlalchemy.orm import Session

from app.rules.matching import check_matching
from app.schemas.finding import Finding
from app.schemas.invoice import ExtractedInvoice
from app.services.master_data import (
    load_previously_invoiced_quantity,
    load_purchase_orders,
    load_received_quantity,
)


def match(
    db: Session, invoice: ExtractedInvoice, exclude_invoice_id: uuid.UUID | None = None
) -> list[Finding]:
    return check_matching(
        invoice,
        load_purchase_orders(db),
        load_received_quantity(db),
        load_previously_invoiced_quantity(db, exclude_invoice_id),
    )
