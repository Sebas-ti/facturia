"""API key auth for the Power Automate flow (docs/spec.md §6).

Applied only to `POST /api/invoices`: it's the one endpoint an external
service (Power Automate) calls. The web also uses this same endpoint and
key for now (no login/Entra ID yet — spec's other stated option for the
web), sent via a build-time env var; the other endpoints stay open until
that exists.
"""

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="API key inválida o ausente.")
