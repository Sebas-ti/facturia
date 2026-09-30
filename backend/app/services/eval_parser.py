import json
import re
from pathlib import Path

from app.schemas.evals import (
    ConfusionMatrixData,
    ConfusionMatrixRow,
    EvalReportDetail,
    EvalReportsResponse,
    EvalReportSummary,
    FieldAccuracyItem,
    FindingAccuracyItem,
    InvoiceCaseResult,
)

REPORTS_DIR = Path(__file__).resolve().parents[3] / "evals" / "reports"


def get_available_reports() -> list[Path]:
    if not REPORTS_DIR.exists():
        return []
    # Sort by modification time descending
    files = list(REPORTS_DIR.glob("*.md"))
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return files


def parse_report_file(file_path: Path, is_latest: bool = False) -> EvalReportDetail:
    content = file_path.read_text(encoding="utf-8")
    filename = file_path.name
    report_id = file_path.stem

    json_path = file_path.with_suffix(".json")
    if json_path.exists():
        return _parse_from_json(json_path, content, filename, report_id)
    return _parse_from_markdown(content, filename, report_id)


def _parse_from_json(json_path: Path, raw_markdown: str, filename: str, report_id: str) -> EvalReportDetail:
    """`evals/run_evals.py` writes this JSON next to the `.md` report — real
    structured data, not something inferred by matching prose. Reports
    generated before this existed (no `.json` sibling) fall back to
    `_parse_from_markdown` below."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return EvalReportDetail(
        id=report_id,
        filename=filename,
        title=data["title"],
        generated_at=data["generated_at"],
        mode=data["mode"],
        summary=data["summary"],
        overall_accuracy_pct=data["overall_accuracy_pct"],
        total_cases=data["total_cases"],
        successful_cases=data["successful_cases"],
        raw_markdown=raw_markdown,
        extraction_accuracy=[FieldAccuracyItem(**f) for f in data["extraction_accuracy"]],
        findings_accuracy=[FindingAccuracyItem(**f) for f in data["findings_accuracy"]],
        confusion_matrix=ConfusionMatrixData(
            labels=data["confusion_matrix"]["labels"],
            rows=[ConfusionMatrixRow(**r) for r in data["confusion_matrix"]["rows"]],
            accuracy_pct=data["confusion_matrix"]["accuracy_pct"],
            correct=data["confusion_matrix"]["correct"],
            total=data["confusion_matrix"]["total"],
        ),
        invoice_cases=[InvoiceCaseResult(**c) for c in data["invoice_cases"]],
    )


def _parse_from_markdown(content: str, filename: str, report_id: str) -> EvalReportDetail:
    """Legacy path for reports generated before `run_evals.py` also wrote a
    `.json` companion (`2026-09-30.md`, `2026-09-30-live-F15.md`). Regex over
    the Markdown prose — fragile by nature, kept only for those old files."""
    # 1. Header / Title
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Reporte de Evaluación"

    # 2. Timestamp
    gen_match = re.search(r"Generado:\s*([^\r\n]+)", content)
    generated_at = gen_match.group(1).strip() if gen_match else ""

    # 3. Mode
    mode = "live" if "--live" in content else "mock"

    # 4. Summary description paragraph
    summary_match = re.search(
        r"Generado:[^\r\n]+\s*\n\s*\n([^\n#]+)", content, re.MULTILINE
    )
    summary = summary_match.group(1).strip() if summary_match else ""

    # 5. Extraction accuracy
    extraction_items: list[FieldAccuracyItem] = []
    field_pattern = re.compile(
        r"^\|\s*`([a-zA-Z0-9_]+)`\s*\|\s*([0-9.]+)%?\s*\|\s*(\d+)\s*/\s*(\d+)\s*\|",
        re.MULTILINE,
    )
    for m in field_pattern.finditer(content):
        extraction_items.append(
            FieldAccuracyItem(
                field=m.group(1),
                precision_pct=float(m.group(2)),
                hits=int(m.group(3)),
                total=int(m.group(4)),
            )
        )

    # 6. Findings precision & recall
    findings_items: list[FindingAccuracyItem] = []
    finding_pattern = re.compile(
        r"^\|\s*`([a-zA-Z0-9_]+)`\s*\|\s*([0-9.]+)%?\s*\|\s*([0-9.]+)%?\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
        re.MULTILINE,
    )
    for m in finding_pattern.finditer(content):
        findings_items.append(
            FindingAccuracyItem(
                code=m.group(1),
                precision_pct=float(m.group(2)),
                recall_pct=float(m.group(3)),
                tp=int(m.group(4)),
                fp=int(m.group(5)),
                fn=int(m.group(6)),
            )
        )

    # 7. Confusion matrix & Decision accuracy
    dec_acc_match = re.search(
        r"matriz de confusión\s*\(([0-9.]+)%?,\s*(\d+)/(\d+)\)", content
    )
    if dec_acc_match:
        accuracy_pct = float(dec_acc_match.group(1))
        correct = int(dec_acc_match.group(2))
        total = int(dec_acc_match.group(3))
    else:
        # Fallback to invoice cases counts
        accuracy_pct = 0.0
        correct = 0
        total = 0

    matrix_rows: list[ConfusionMatrixRow] = []
    matrix_pattern = re.compile(
        r"^\|\s*(APROBAR|REVISION|RECHAZAR)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
        re.MULTILINE,
    )
    for m in matrix_pattern.finditer(content):
        matrix_rows.append(
            ConfusionMatrixRow(
                expected=m.group(1),
                aprobar=int(m.group(2)),
                revision=int(m.group(3)),
                rechazar=int(m.group(4)),
            )
        )

    confusion_matrix = ConfusionMatrixData(
        labels=["APROBAR", "REVISION", "RECHAZAR"],
        rows=matrix_rows,
        accuracy_pct=accuracy_pct,
        correct=correct,
        total=total,
    )

    # 8. Invoice Cases
    case_header_match = re.search(
        r"Resultado por factura\s*\((\d+)/(\d+)\s*sin diferencias\)", content
    )
    if case_header_match and total == 0:
        correct = int(case_header_match.group(1))
        total = int(case_header_match.group(2))
        accuracy_pct = round((correct / total) * 100.0, 1) if total else 0.0

    cases_items: list[InvoiceCaseResult] = []
    case_pattern = re.compile(
        r"^\|\s*([A-Za-z0-9_-]+)\s*\|\s*(OK|FALLA)\s*\|\s*(.*?)\s*\|",
        re.MULTILINE,
    )
    for m in case_pattern.finditer(content):
        inv_id = m.group(1).strip()
        if inv_id.lower() in ("factura", "invoice"):
            continue
        cases_items.append(
            InvoiceCaseResult(
                invoice_id=inv_id,
                status=m.group(2),
                detail=m.group(3).strip(),
            )
        )

    # If case counts are available from cases_items, refine totals
    if cases_items:
        total = len(cases_items)
        correct = sum(1 for c in cases_items if c.status == "OK")
        if not dec_acc_match:
            accuracy_pct = round((correct / total) * 100.0, 1) if total else 0.0

    return EvalReportDetail(
        id=report_id,
        filename=filename,
        title=title,
        generated_at=generated_at,
        mode=mode,
        summary=summary,
        overall_accuracy_pct=accuracy_pct,
        total_cases=total,
        successful_cases=correct,
        raw_markdown=content,
        extraction_accuracy=extraction_items,
        findings_accuracy=findings_items,
        confusion_matrix=confusion_matrix,
        invoice_cases=cases_items,
    )


def load_eval_reports_response(report_id: str | None = None) -> EvalReportsResponse:
    files = get_available_reports()
    if not files:
        # Fallback empty detail
        empty_detail = EvalReportDetail(
            id="none",
            filename="",
            title="Sin reportes disponibles",
            generated_at="",
            mode="mock",
            summary="No se encontraron reportes en evals/reports/.",
            overall_accuracy_pct=0.0,
            total_cases=0,
            successful_cases=0,
            raw_markdown="No hay reportes de evaluación disponibles.",
            extraction_accuracy=[],
            findings_accuracy=[],
            confusion_matrix=ConfusionMatrixData(
                labels=["APROBAR", "REVISION", "RECHAZAR"],
                rows=[],
                accuracy_pct=0.0,
                correct=0,
                total=0,
            ),
            invoice_cases=[],
        )
        return EvalReportsResponse(reports=[], selected=empty_detail)

    summaries: list[EvalReportSummary] = []
    selected_file = files[0]

    for i, file_path in enumerate(files):
        detail = parse_report_file(file_path, is_latest=(i == 0))
        summaries.append(
            EvalReportSummary(
                id=detail.id,
                filename=detail.filename,
                title=detail.title,
                generated_at=detail.generated_at,
                mode=detail.mode,
                total_cases=detail.total_cases,
                successful_cases=detail.successful_cases,
                accuracy_pct=detail.overall_accuracy_pct,
                is_latest=(i == 0),
            )
        )
        if report_id and (report_id == detail.id or report_id == detail.filename):
            selected_file = file_path

    selected_detail = parse_report_file(selected_file, is_latest=(selected_file == files[0]))

    return EvalReportsResponse(reports=summaries, selected=selected_detail)
