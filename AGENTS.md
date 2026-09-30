# FacturIA — Guía para agentes de código

Este archivo lo leen Claude Code (vía `CLAUDE.md`) y Antigravity. Es la fuente única de reglas del proyecto.

## Qué es
Sistema multiagente de procesamiento de facturas de proveedores (Accounts Payable): extrae datos de PDFs, valida contra órdenes de compra y recepciones, detecta fraude y decide APROBAR / REVISION / RECHAZAR con explicación. Es el proyecto principal del portafolio de Sebastián (AI Engineer junior, Colombia).

- Especificación completa: `docs/spec.md` (léela antes de diseñar algo nuevo).
- Datos de prueba y ground truth: `data/` (ver `data/README.md`). Todo es ficticio.
- Estado actual y siguiente tarea: `PROGRESS.md`.

## Sobre el desarrollador
- Sabe Python, Django, React, Node, Azure AI (AI-102), RPA (UiPath, Power Automate), RAG.
- Está aprendiendo FastAPI profesional, LangGraph, Docker, CI/CD y evals: explica brevemente lo nuevo la primera vez que aparezca.
- Conversación en español. Código, identificadores, commits y comentarios en inglés.

## Stack (no cambiar sin proponerlo y justificarlo)
- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic, PostgreSQL 16, gestor `uv`.
- Agentes: LangGraph; Azure OpenAI (modelo mini) con salidas estructuradas.
- Extracción: Azure AI Document Intelligence `prebuilt-invoice` + normalización LLM.
- Archivos: Azure Blob Storage (Azurite en local).
- Frontend: React + Vite + TypeScript + Tailwind + TanStack Query.
- Infra: Docker Compose local; Azure Container Apps + Static Web Apps; GitHub Actions.
- Calidad: pytest, Ruff, mypy.

## Estructura
```
backend/app/{api,agents,rules,schemas,db,services}/  backend/tests/
frontend/   evals/   data/   docs/   scripts/   automation/   infra/
```

## Comandos
```bash
docker compose up -d db azurite              # servicios locales
cd backend && uv sync                        # dependencias
cd backend && uv run pytest                  # tests
cd backend && uv run ruff check . && uv run mypy app
uv run python evals/run_evals.py --mock      # evals sin gastar créditos de Azure
```
(Actualiza esta sección cuando los comandos cambien.)

## Reglas de diseño
1. Validaciones calculables (DV del NIT, aritmética, match con OC/recepción, duplicados, cuenta bancaria) = **código determinista** en `backend/app/rules/`, funciones puras y 100 % testeadas. El LLM solo extrae, normaliza, explica y redacta.
2. Toda salida de LLM se valida con Pydantic. Nunca parsear texto libre.
3. Dinero con `Decimal`, nunca `float`.
4. Los códigos de hallazgo y la matriz de decisión están en `docs/spec.md` §4. No inventes códigos nuevos sin agregarlos allí.
5. Secretos solo en variables de entorno; mantener `.env.example` actualizado.
6. No leer los PDFs de `data/facturas/` ni llamar a Azure salvo que la tarea lo requiera; usar `ground_truth.json` y el modo mock.

## Forma de trabajar
- Una tarea de `PROGRESS.md` a la vez. Antes de una tarea grande, proponer un plan corto y esperar aprobación.
- Cada funcionalidad con sus tests; no marcar una tarea como hecha si los tests fallan.
- Al terminar una tarea: correr tests y lint, actualizar `PROGRESS.md` (hecho, decisiones, siguiente paso) y proponer un commit con mensaje convencional (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
- Si algo contradice `docs/spec.md`, avisar antes de continuar.
- Señalar cuando algo sea bueno para mostrar en el README, LinkedIn o una entrevista.
