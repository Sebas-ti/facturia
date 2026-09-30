from typing import Any

import pytest

from app.schemas import ExtractedInvoice
from tests.ground_truth import load_facturas, map_extracted_invoice


@pytest.mark.parametrize("factura", load_facturas(), ids=lambda factura: factura["id"])
def test_ground_truth_esperado_validates_as_extracted_invoice(
    factura: dict[str, Any],
) -> None:
    mapped = map_extracted_invoice(factura["esperado"])
    invoice = ExtractedInvoice(**mapped)
    assert invoice.invoice_number == factura["esperado"]["numero_factura"]
