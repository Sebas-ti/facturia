"""Wraps a graph node with timing and a persisted app.db.models.AgentRun
trace row (docs/spec.md §5).

Requires an `invoices` row for `state["invoice_id"]` to already exist
(AgentRun.invoice_id is a real foreign key) — the caller creates a
placeholder Invoice row before running the graph and updates it with the
final result afterward; that orchestration lives at the API layer (Fase 4),
not here.

Token counts are left null for now: the LLM clients (app.services.llm,
app.services.explain) don't surface usage stats back to their callers yet.
"""

import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import AgentRun


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _to_jsonable(v) for key, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    return value


def traced[StateT: Mapping[str, Any]](
    db: Session, node_name: str, node: Callable[[StateT], dict[str, Any]]
) -> Callable[[StateT], dict[str, Any]]:
    def wrapper(state: StateT) -> dict[str, Any]:
        started_at = datetime.now(UTC)
        start = time.perf_counter()
        output = node(state)
        duration_ms = round((time.perf_counter() - start) * 1000)

        db.add(
            AgentRun(
                invoice_id=state["invoice_id"],
                node=node_name,
                started_at=started_at,
                duration_ms=duration_ms,
                output=_to_jsonable(output),
            )
        )
        db.commit()

        return output

    return wrapper
