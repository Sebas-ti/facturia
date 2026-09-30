"""Tests for GET /api/evals endpoint (docs/spec.md §9)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_evals_list_and_selected() -> None:
    response = client.get("/api/evals")
    assert response.status_code == 200
    data = response.json()

    assert "reports" in data
    assert "selected" in data
    assert len(data["reports"]) >= 1

    selected = data["selected"]
    assert selected["id"]
    assert selected["filename"].endswith(".md")
    assert selected["title"]
    assert selected["mode"] in ("mock", "live")
    assert len(selected["extraction_accuracy"]) > 0
    assert len(selected["invoice_cases"]) > 0
    assert selected["raw_markdown"]


def test_get_evals_specific_report() -> None:
    # 2026-09-30.md is the 100% full-pipeline mock evaluation
    response = client.get("/api/evals?report_id=2026-09-30")
    assert response.status_code == 200
    data = response.json()

    selected = data["selected"]
    assert selected["id"] == "2026-09-30"
    assert selected["mode"] == "mock"
    assert selected["overall_accuracy_pct"] == 100.0
    assert selected["total_cases"] == 15
    assert selected["successful_cases"] == 15

    # 18 fields: 12 invoice level + 6 line level
    assert len(selected["extraction_accuracy"]) == 18
    for field in selected["extraction_accuracy"]:
        assert field["precision_pct"] == 100.0

    # 8 finding codes tested in the dataset
    assert len(selected["findings_accuracy"]) == 8
    for finding in selected["findings_accuracy"]:
        assert finding["precision_pct"] == 100.0
        assert finding["recall_pct"] == 100.0

    # Confusion matrix
    matrix = selected["confusion_matrix"]
    assert matrix["accuracy_pct"] == 100.0
    assert matrix["correct"] == 15
    assert matrix["total"] == 15
    assert len(matrix["rows"]) == 3

    # Invoice cases
    assert len(selected["invoice_cases"]) == 15
    assert all(c["status"] == "OK" for c in selected["invoice_cases"])


def test_get_eval_report_by_path_param() -> None:
    response = client.get("/api/evals/2026-09-30")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "2026-09-30"
    assert data["filename"] == "2026-09-30.md"
    assert data["overall_accuracy_pct"] == 100.0


def test_get_eval_report_not_found() -> None:
    response = client.get("/api/evals/non_existent_report_xyz")
    assert response.status_code == 404
    data = response.json()
    assert "no encontrado" in data["detail"].lower()
