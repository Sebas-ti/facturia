"""Postgres-backed LangGraph checkpointer for human-in-the-loop (docs/spec.md
§2.1): a REVISION decision pauses the graph via `interrupt()`; the analyst's
action resumes it from exactly where it paused, via the same thread_id.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from app.config import settings
from app.schemas.finding import Finding, FindingCode
from app.schemas.invoice import BankAccount, ExtractedInvoice, InvoiceLine

# Without this, the checkpointer's msgpack serializer logs a deprecation
# warning for every Pydantic/enum type it hasn't seen before — and a future
# langgraph version will refuse to deserialize them at all.
_SERDE = JsonPlusSerializer(
    allowed_msgpack_modules=[Finding, FindingCode, ExtractedInvoice, InvoiceLine, BankAccount]
)


def _psycopg_conn_string() -> str:
    # PostgresSaver wants a plain psycopg DSN, not the "+psycopg" SQLAlchemy
    # dialect URL app.config.settings.database_url is written for.
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


@contextmanager
def build_checkpointer() -> Iterator[PostgresSaver]:
    with PostgresSaver.from_conn_string(_psycopg_conn_string()) as saver:
        saver.serde = _SERDE
        saver.setup()
        yield saver
