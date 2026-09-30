"""Tests for master data endpoints (GET /api/suppliers, GET /api/purchase-orders)."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_suppliers() -> None:
    response = client.get("/api/suppliers")
    assert response.status_code == 200
    suppliers = response.json()
    assert len(suppliers) >= 6

    nit_list = [s["nit"] for s in suppliers]
    assert "900482113" in nit_list  # Papelería El Cóndor S.A.S.

    # Check fields
    s1 = next(s for s in suppliers if s["nit"] == "900482113")
    assert s1["name"] == "Papelería El Cóndor S.A.S."
    assert s1["dv"] == 6
    assert s1["bank"] == "Bancolombia"
    assert s1["status"] == "ACTIVO"
    assert s1["purchase_orders_count"] >= 1


def test_list_suppliers_search() -> None:
    response = client.get("/api/suppliers?search=Cóndor")
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert any("Cóndor" in s["name"] for s in results)

    # Search by NIT
    response_nit = client.get("/api/suppliers?search=900482113")
    assert response_nit.status_code == 200
    assert len(response_nit.json()) == 1


def test_get_supplier_detail() -> None:
    # Get first supplier id
    suppliers = client.get("/api/suppliers").json()
    assert len(suppliers) > 0
    supplier_id = suppliers[0]["id"]

    response = client.get(f"/api/suppliers/{supplier_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == supplier_id
    assert "name" in data


def test_get_supplier_not_found() -> None:
    random_id = str(uuid4())
    response = client.get(f"/api/suppliers/{random_id}")
    assert response.status_code == 404


def test_list_purchase_orders() -> None:
    response = client.get("/api/purchase-orders")
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) >= 11  # 11 POs seeded

    po_numbers = [po["number"] for po in orders]
    assert "OC-2026-0101" in po_numbers

    po1 = next(po for po in orders if po["number"] == "OC-2026-0101")
    assert po1["supplier_nit"] == "900482113"
    assert po1["lines_count"] >= 1
    assert len(po1["lines"]) == po1["lines_count"]

    first_line = po1["lines"][0]
    assert "sku" in first_line
    assert "quantity" in first_line
    assert "unit_price" in first_line
    assert "quantity_received" in first_line
    assert float(first_line["quantity_received"]) > 0


def test_list_purchase_orders_filters() -> None:
    # Filter by number
    res_num = client.get("/api/purchase-orders?number=OC-2026-0101")
    assert res_num.status_code == 200
    orders = res_num.json()
    assert len(orders) == 1
    assert orders[0]["number"] == "OC-2026-0101"

    # Filter by supplier nit
    res_supp = client.get("/api/purchase-orders?supplier_nit=900482113")
    assert res_supp.status_code == 200
    for order in res_supp.json():
        assert order["supplier_nit"] == "900482113"


def test_get_purchase_order_by_number_and_id() -> None:
    # By number
    response = client.get("/api/purchase-orders/OC-2026-0101")
    assert response.status_code == 200
    data = response.json()
    assert data["number"] == "OC-2026-0101"

    # By ID
    po_id = data["id"]
    res_id = client.get(f"/api/purchase-orders/{po_id}")
    assert res_id.status_code == 200
    assert res_id.json()["number"] == "OC-2026-0101"


def test_get_purchase_order_not_found() -> None:
    response = client.get("/api/purchase-orders/OC-NON-EXISTENT")
    assert response.status_code == 404
