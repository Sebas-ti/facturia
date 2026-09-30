# PROGRESS — FacturIA

> Archivo de relevo entre Claude Code y Antigravity. Actualizarlo al terminar cada tarea.

## Estado actual
- **Fase:** 1 · Base
- **Última herramienta usada:** Claude Code
- **Siguiente paso:** Tarea 1.3

## Fase 1 · Base (días 1–3)
- [x] **1.1 Esqueleto backend:** `backend/` con `uv`, `pyproject.toml` (fastapi, uvicorn, pydantic, pydantic-settings, sqlalchemy, alembic, psycopg, pytest, ruff, mypy), `app/main.py` con `GET /api/health` y su test.
- [x] **1.2 Docker Compose:** servicios `db` (Postgres 16) y `azurite`; `.env.example`; `app/config.py` con pydantic-settings.
- [ ] **1.3 Esquemas Pydantic:** `app/schemas/` con `InvoiceLine`, `BankAccount`, `ExtractedInvoice`, `Finding`, `FindingCode` (enum), `Decision` según spec §3–4. Test: los `esperado` de `data/ground_truth.json` validan contra `ExtractedInvoice` (mapeando nombres de campos).
- [ ] **1.4 Regla NIT:** `app/rules/nit.py` (`nit_check_digit`, `validate_nit`) con tests, incluidos los NITs de `data/proveedores.csv`.
- [ ] **1.5 Regla aritmética:** `app/rules/arithmetic.py` → lista de `Finding` (`ARITHMETIC_ERROR`), tolerancia $1. Test con F10 (falla) y F01 (pasa).
- [ ] **1.6 Reglas de matching y riesgo:** `app/rules/matching.py` (`PRICE_MISMATCH` 2 %, `QTY_EXCEEDS_RECEIPT` acumulado, `MISSING_PO`) y `app/rules/risk.py` (`UNKNOWN_SUPPLIER`, `DUPLICATE_INVOICE`, `BANK_ACCOUNT_CHANGED`). Funciones puras que reciben los datos maestros como parámetros.
- [ ] **1.7 Decisor:** `app/rules/decision.py` con la matriz de spec §4.2 (incluye `AMOUNT_OVER_THRESHOLD`).
- [ ] **1.8 Test de integración de reglas:** recorrer F01→F15 de `ground_truth.json` aplicando todas las reglas; debe dar 15/15 en hallazgos y decisión.
- [ ] **1.9 Base de datos:** modelos SQLAlchemy de spec §5, migración Alembic inicial, `scripts/seed.py` que carga `data/`.
- [ ] **1.10 CI:** `.github/workflows/ci.yml` con ruff, mypy y pytest.

## Fases siguientes (desglosar al llegar)
2. Extracción (Doc Intelligence + LLM, evals de extracción) · 3. Grafo LangGraph + human-in-the-loop · 4. Web React · 5. Power Automate + despliegue Azure · 6. Portafolio.

## Decisiones tomadas
- 2026-09-30 — Se agregan los códigos `INVALID_CUFE` (ALTA) e `INCOHERENT_DATES` (MEDIA) a `docs/spec.md` §4.1 — el nodo `validate` (§2.1) ya mencionaba validar CUFE y coherencia de fechas pero la tabla de hallazgos no tenía códigos para esos casos.
- 2026-09-30 — `backend/pyproject.toml` usa `[tool.uv] package = false` (proyecto de aplicación, no librería instalable) con `app/` como paquete plano en la raíz de `backend/`, en vez del layout `src/` que genera `uv init` por defecto — así coincide con la estructura de AGENTS.md (`backend/app/...`).
- 2026-09-30 — En esta máquina, `uv run pytest` falla con "Una directiva de Control de aplicaciones bloqueó este archivo" (bloquea `pytest.exe` del venv, no a `ruff`/`mypy`). Workaround: `uv run python -m pytest`. No se cambia el comando en AGENTS.md porque es una política local de Windows, no algo del proyecto.
- 2026-09-30 — `.env.example` lo creó el usuario manualmente (Claude Code tiene una regla de permisos que bloquea `Write`/`Edit` sobre archivos `.env*`, incluido el `.example`); Claude solo entregó el contenido propuesto.
- 2026-09-30 — `docker compose up -d db azurite` sin verificar de extremo a extremo: el CLI y `docker compose config` validan bien, pero justo después de instalar Docker Desktop el motor (`dockerDesktopLinuxEngine`) no respondía todavía. Pendiente que el usuario confirme que los contenedores levantan tras completar el setup inicial de Docker Desktop.

## Registro de sesiones
| Fecha | Herramienta | Hecho | Notas |
|---|---|---|---|
| 2026-09-30 | Claude Code | Agregados `INVALID_CUFE`/`INCOHERENT_DATES` a spec §4.1. Tarea 1.1: esqueleto `backend/` con uv, FastAPI, `GET /api/health` + test. | pytest/ruff/mypy en verde. Instalado `uv` (no estaba en la máquina). |
| 2026-09-30 | Claude Code | Tarea 1.2: `docker-compose.yml` (db + azurite), `.env.example` (creado por el usuario), `app/config.py` con pydantic-settings + tests. | Docker recién instalado por el usuario; motor no respondía aún, falta confirmar `docker compose up -d db azurite`. |
