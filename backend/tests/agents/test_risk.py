from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.agents.risk import risk
from app.db.models import Invoice, Supplier
from app.db.session import SessionLocal
from app.schemas.finding import FindingCode
from scripts.seed import seed
from tests.ground_truth import extracted_invoice

_TEST_FILE_HASH_PREFIX = "test-risk-"


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Requires `docker compose up -d db` and `alembic upgrade head` (see AGENTS.md)."""
    with SessionLocal() as session:
        seed(session)
        yield session
        session.execute(
            delete(Invoice).where(Invoice.file_hash.like(f"{_TEST_FILE_HASH_PREFIX}%"))
        )
        session.commit()


def test_f01_clean_supplier_has_no_findings(db: Session) -> None:
    assert risk(db, extracted_invoice("F01"), f"{_TEST_FILE_HASH_PREFIX}f01") == []


def test_f12_unknown_supplier_against_seeded_data(db: Session) -> None:
    findings = risk(db, extracted_invoice("F12"), f"{_TEST_FILE_HASH_PREFIX}f12")
    assert [f.code for f in findings] == [FindingCode.UNKNOWN_SUPPLIER]


def test_f13_bank_account_changed_against_seeded_data(db: Session) -> None:
    findings = risk(db, extracted_invoice("F13"), f"{_TEST_FILE_HASH_PREFIX}f13")
    assert [f.code for f in findings] == [FindingCode.BANK_ACCOUNT_CHANGED]


def test_duplicate_invoice_detected_against_a_previously_stored_invoice(db: Session) -> None:
    condor_id = db.scalars(select(Supplier.id).where(Supplier.nit == "900482113")).one()
    f01 = extracted_invoice("F01")
    original = Invoice(
        file_hash=f"{_TEST_FILE_HASH_PREFIX}original",
        blob_url="http://example.invalid/fake.pdf",
        status="PROCESSED",
        decision="APROBAR",
        supplier_id=condor_id,
        invoice_number=f01.invoice_number,
        total=Decimal(1000),
        extracted={"purchase_order": f01.purchase_order, "lines": []},
    )
    db.add(original)
    db.commit()

    findings = risk(db, f01, f"{_TEST_FILE_HASH_PREFIX}f01-again")

    assert [f.code for f in findings] == [FindingCode.DUPLICATE_INVOICE]
    assert findings[0].severity == "CRITICA"


def test_exclude_invoice_id_excludes_itself_from_duplicate_check(db: Session) -> None:
    condor_id = db.scalars(select(Supplier.id).where(Supplier.nit == "900482113")).one()
    f01 = extracted_invoice("F01")
    self_invoice = Invoice(
        file_hash=f"{_TEST_FILE_HASH_PREFIX}self",
        blob_url="http://example.invalid/fake.pdf",
        status="PROCESSED",
        decision=None,
        supplier_id=condor_id,
        invoice_number=f01.invoice_number,
        total=Decimal(1000),
        extracted={"purchase_order": f01.purchase_order, "lines": []},
    )
    db.add(self_invoice)
    db.commit()

    findings = risk(
        db, f01, f"{_TEST_FILE_HASH_PREFIX}self", exclude_invoice_id=self_invoice.id
    )

    assert findings == []
