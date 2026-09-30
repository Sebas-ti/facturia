import csv
from pathlib import Path

import pytest

from app.rules.nit import nit_check_digit, validate_nit

PROVEEDORES_PATH = Path(__file__).parents[3] / "data" / "proveedores.csv"


def _load_proveedores_nit_dv() -> list[tuple[str, int]]:
    with PROVEEDORES_PATH.open(encoding="utf-8") as f:
        return [(row["nit"], int(row["dv"])) for row in csv.DictReader(f)]


@pytest.mark.parametrize("nit, dv", _load_proveedores_nit_dv())
def test_proveedores_dv_is_valid(nit: str, dv: int) -> None:
    assert nit_check_digit(nit) == dv
    assert validate_nit(nit, dv) is True


def test_comprador_dv_is_valid() -> None:
    # Distribuciones Andinas Demo S.A.S., data/ground_truth.json "comprador".
    assert nit_check_digit("901555321") == 1


def test_validate_nit_rejects_wrong_dv() -> None:
    # F11: DV impreso (6) no coincide con el DV real del maestro (3).
    assert validate_nit("901338820", 6) is False


def test_nit_check_digit_rejects_non_digits() -> None:
    with pytest.raises(ValueError, match="only digits"):
        nit_check_digit("90048211X")


def test_nit_check_digit_rejects_empty() -> None:
    with pytest.raises(ValueError, match="1-15 digits"):
        nit_check_digit("")


def test_nit_check_digit_rejects_too_long() -> None:
    with pytest.raises(ValueError, match="1-15 digits"):
        nit_check_digit("1" * 16)
