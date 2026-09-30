from pydantic import BaseModel


class EvalReportSummary(BaseModel):
    id: str
    filename: str
    title: str
    generated_at: str
    mode: str
    total_cases: int
    successful_cases: int
    accuracy_pct: float
    is_latest: bool = False


class FieldAccuracyItem(BaseModel):
    field: str
    precision_pct: float
    hits: int
    total: int


class FindingAccuracyItem(BaseModel):
    code: str
    precision_pct: float
    recall_pct: float
    tp: int
    fp: int
    fn: int


class ConfusionMatrixRow(BaseModel):
    expected: str
    aprobar: int
    revision: int
    rechazar: int


class ConfusionMatrixData(BaseModel):
    labels: list[str]
    rows: list[ConfusionMatrixRow]
    accuracy_pct: float
    correct: int
    total: int


class InvoiceCaseResult(BaseModel):
    invoice_id: str
    status: str
    detail: str


class EvalReportDetail(BaseModel):
    id: str
    filename: str
    title: str
    generated_at: str
    mode: str
    summary: str
    overall_accuracy_pct: float
    total_cases: int
    successful_cases: int
    raw_markdown: str
    extraction_accuracy: list[FieldAccuracyItem]
    findings_accuracy: list[FindingAccuracyItem]
    confusion_matrix: ConfusionMatrixData
    invoice_cases: list[InvoiceCaseResult]


class EvalReportsResponse(BaseModel):
    reports: list[EvalReportSummary]
    selected: EvalReportDetail
