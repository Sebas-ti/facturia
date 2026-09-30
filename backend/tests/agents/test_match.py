from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session

from app.agents.match import match
from app.db.session import SessionLocal
from app.schemas.finding import FindingCode
from scripts.seed import seed
from tests.ground_truth import extracted_invoice


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Requires `docker compose up -d db` and `alembic upgrade head` (see AGENTS.md)."""
    with SessionLocal() as session:
        seed(session)
        yield session


def test_f01_matches_cleanly_against_seeded_data(db: Session) -> None:
    assert match(db, extracted_invoice("F01")) == []


def test_f07_price_mismatch_against_seeded_data(db: Session) -> None:
    findings = match(db, extracted_invoice("F07"))
    assert [f.code for f in findings] == [FindingCode.PRICE_MISMATCH]


def test_f08_qty_exceeds_receipt_against_seeded_data(db: Session) -> None:
    findings = match(db, extracted_invoice("F08"))
    assert [f.code for f in findings] == [FindingCode.QTY_EXCEEDS_RECEIPT]


def test_f14_missing_po_against_seeded_data(db: Session) -> None:
    findings = match(db, extracted_invoice("F14"))
    assert [f.code for f in findings] == [FindingCode.MISSING_PO]
