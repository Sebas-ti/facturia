"""`risk` node (docs/spec.md §2.1): proveedor en maestro, factura duplicada,
cuenta bancaria distinta — conciliado contra Postgres."""

import uuid

from sqlalchemy.orm import Session

from app.rules.risk import (
    check_bank_account_changed,
    check_duplicate_invoice,
    check_unknown_supplier,
)
from app.schemas.finding import Finding
from app.schemas.invoice import ExtractedInvoice
from app.services.master_data import (
    load_previous_file_hashes,
    load_previous_invoice_numbers,
    load_suppliers,
)


def risk(
    db: Session,
    invoice: ExtractedInvoice,
    file_hash: str,
    exclude_invoice_id: uuid.UUID | None = None,
) -> list[Finding]:
    suppliers = load_suppliers(db)
    return [
        *check_unknown_supplier(invoice, suppliers),
        *check_duplicate_invoice(
            invoice,
            file_hash,
            load_previous_invoice_numbers(db, exclude_invoice_id),
            load_previous_file_hashes(db, exclude_invoice_id),
        ),
        *check_bank_account_changed(invoice, suppliers),
    ]
