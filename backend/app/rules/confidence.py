from app.schemas.finding import Finding, FindingCode

CONFIDENCE_THRESHOLD = 0.80
CRITICAL_FIELDS = ("supplier_nit", "invoice_number", "total")


def check_low_confidence(field_confidence: dict[str, float]) -> list[Finding]:
    low_confidence = {
        field: field_confidence[field]
        for field in CRITICAL_FIELDS
        if field in field_confidence and field_confidence[field] < CONFIDENCE_THRESHOLD
    }

    if not low_confidence:
        return []

    return [
        Finding(
            code=FindingCode.LOW_CONFIDENCE_EXTRACTION,
            severity="MEDIA",
            message="Uno o más campos críticos se extrajeron con baja confianza.",
            evidence={
                "umbral": CONFIDENCE_THRESHOLD,
                "campos": low_confidence,
            },
        )
    ]
