from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    action: Literal["APROBAR", "RECHAZAR"] = Field(
        ..., description="Acción del analista: APROBAR o RECHAZAR"
    )
    comment: str | None = Field(default=None, description="Comentario o justificación del analista")
    reviewer: str = Field(default="analyst@facturia.local", description="Identificador del analista")


class ReviewResponse(BaseModel):
    id: UUID
    invoice_id: UUID
    reviewer: str
    action: str
    comment: str | None = None
    created_at: datetime
    previous_decision: str | None = None
    new_decision: str
