from app.schemas.finding import Finding, FindingCode
from app.schemas.invoice import ExtractedInvoice
from app.schemas.supplier import Supplier


def check_unknown_supplier(
    invoice: ExtractedInvoice, suppliers: dict[str, Supplier]
) -> list[Finding]:
    supplier = suppliers.get(invoice.supplier_nit)
    if supplier is not None and supplier.status == "ACTIVO":
        return []

    return [
        Finding(
            code=FindingCode.UNKNOWN_SUPPLIER,
            severity="ALTA",
            message="El proveedor no está registrado o no está activo en el maestro.",
            evidence={
                "nit": invoice.supplier_nit,
                "encontrado": supplier is not None,
                "estado": supplier.status if supplier is not None else None,
            },
        )
    ]


def check_duplicate_invoice(
    invoice: ExtractedInvoice,
    file_hash: str,
    previous_invoice_numbers: set[tuple[str, str]],
    previous_file_hashes: set[str],
) -> list[Finding]:
    same_number = (invoice.supplier_nit, invoice.invoice_number) in previous_invoice_numbers
    same_hash = file_hash in previous_file_hashes
    if not same_number and not same_hash:
        return []

    return [
        Finding(
            code=FindingCode.DUPLICATE_INVOICE,
            severity="CRITICA",
            message="Esta factura ya fue procesada (mismo NIT + número, o mismo archivo).",
            evidence={
                "nit": invoice.supplier_nit,
                "numero_factura": invoice.invoice_number,
                "mismo_numero": same_number,
                "mismo_hash": same_hash,
            },
        )
    ]


def check_bank_account_changed(
    invoice: ExtractedInvoice, suppliers: dict[str, Supplier]
) -> list[Finding]:
    supplier = suppliers.get(invoice.supplier_nit)
    if supplier is None or invoice.bank_account is None:
        return []
    if invoice.bank_account == supplier.bank_account:
        return []

    return [
        Finding(
            code=FindingCode.BANK_ACCOUNT_CHANGED,
            severity="CRITICA",
            message="La cuenta bancaria de la factura no coincide con la registrada.",
            evidence={
                "cuenta_registrada": supplier.bank_account.model_dump(),
                "cuenta_factura": invoice.bank_account.model_dump(),
            },
        )
    ]
