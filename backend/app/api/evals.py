from fastapi import APIRouter, HTTPException, Query

from app.schemas.evals import EvalReportDetail, EvalReportsResponse
from app.services.eval_parser import (
    get_available_reports,
    load_eval_reports_response,
    parse_report_file,
)

router = APIRouter(prefix="/api/evals", tags=["evals"])


@router.get("", response_model=EvalReportsResponse)
def get_evals(
    report_id: str | None = Query(
        default=None, description="ID o nombre del reporte a consultar (opcional, por defecto el último)"
    ),
) -> EvalReportsResponse:
    return load_eval_reports_response(report_id)


@router.get("/{report_id}", response_model=EvalReportDetail)
def get_eval_report(report_id: str) -> EvalReportDetail:
    files = get_available_reports()
    target_file = next(
        (f for f in files if f.stem == report_id or f.name == report_id), None
    )
    if not target_file:
        raise HTTPException(
            status_code=404, detail=f"Reporte de evaluación '{report_id}' no encontrado."
        )

    is_latest = len(files) > 0 and files[0] == target_file
    return parse_report_file(target_file, is_latest=is_latest)
