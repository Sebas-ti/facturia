import hashlib
from datetime import date
from decimal import Decimal

import pytest

from app.services.normalize import (
    extract_cufe,
    normalize_invoice_number,
    parse_cop_amount,
    parse_invoice_date,
    split_nit_and_dv,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("$ 1.425.620,00", Decimal("1425620.00")),
        ("1.425.620,00", Decimal("1425620.00")),
        ("18.500", Decimal(18500)),
        ("18.500,00", Decimal("18500.00")),
        ("40", Decimal(40)),
        ("19%", Decimal(19)),
        ("0,00", Decimal("0.00")),
        ("40.5", Decimal("40.5")),
        ("-1.500", Decimal(-1500)),
    ],
)
def test_parse_cop_amount(raw: str, expected: Decimal) -> None:
    assert parse_cop_amount(raw) == expected


def test_parse_cop_amount_rejects_empty_string() -> None:
    with pytest.raises(ValueError, match="Empty amount"):
        parse_cop_amount("  $ ")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("FEPC 1045", "FEPC-1045"),
        ("No. TRS-20871", "TRS-20871"),
        ("LTV11502", "LTV-11502"),
        ("FACTURA ELECTRÓNICA DE VENTA N° LTV 11502", "LTV-11502"),
    ],
)
def test_normalize_invoice_number(raw: str, expected: str) -> None:
    assert normalize_invoice_number(raw) == expected


def test_normalize_invoice_number_rejects_unrecognizable_input() -> None:
    with pytest.raises(ValueError, match="Could not normalize invoice number"):
        normalize_invoice_number("sin datos")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-09-01", date(2026, 9, 1)),
        ("01/09/2026", date(2026, 9, 1)),
        ("01-09-2026", date(2026, 9, 1)),
    ],
)
def test_parse_invoice_date(raw: str, expected: date) -> None:
    assert parse_invoice_date(raw) == expected


def test_parse_invoice_date_rejects_unrecognizable_input() -> None:
    with pytest.raises(ValueError, match="Could not parse date"):
        parse_invoice_date("25 de agosto de 2026")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("900482113-6", ("900482113", 6)),
        ("900482113 - 6", ("900482113", 6)),
        ("NIT 900482113-6", ("900482113", 6)),
        ("900482113", ("900482113", None)),
    ],
)
def test_split_nit_and_dv(raw: str, expected: tuple[str, int | None]) -> None:
    assert split_nit_and_dv(raw) == expected


def test_split_nit_and_dv_rejects_unrecognizable_input() -> None:
    with pytest.raises(ValueError, match="Could not parse NIT"):
        split_nit_and_dv("sin nit")


def test_extract_cufe_split_across_two_lines_like_the_generated_pdfs() -> None:
    cufe = hashlib.sha384(b"FEPC1045").hexdigest()
    full_text = f"...\nCUFE:\n{cufe[:64]}\n{cufe[64:]}\n..."

    assert extract_cufe(full_text) == cufe


def test_extract_cufe_ignores_qr_dian_label_interleaved_by_ocr_reading_order() -> None:
    """Real Document Intelligence output for F01: the QR code's "QR DIAN"
    label lands between the CUFE's two lines because of page layout, not the
    field's logical shape (see PROGRESS.md 2.7)."""
    cufe = hashlib.sha384(b"FEPC1045").hexdigest()
    full_text = (
        f"...\nCUFE:\n: {cufe[:64]}\nQR DIAN\n{cufe[64:]}\n"
        "Autorización de numeración DIAN No. 18764000000000 (SIMULADA)..."
    )

    assert extract_cufe(full_text) == cufe


def test_extract_cufe_returns_none_when_absent() -> None:
    assert extract_cufe("factura sin CUFE") is None


def test_extract_cufe_returns_none_when_incomplete() -> None:
    assert extract_cufe(f"CUFE:\n{'a' * 50}") is None
