# FacturIA — Especificación técnica

Sistema multiagente que recibe facturas de proveedores (PDF), extrae sus datos, las valida contra las órdenes de compra y las recepciones de almacén, detecta riesgos de fraude y decide si se aprueban automáticamente, pasan a revisión humana o se rechazan, explicando cada decisión.

> **Pitch para el README y LinkedIn:** "Automatización inteligente de cuentas por pagar: RPA para capturar las facturas, IA para entenderlas y reglas deterministas para decidir. Procesa una factura en segundos con trazabilidad completa de cada decisión."

---

## 1. Problema de negocio

En cuentas por pagar, una persona recibe facturas por correo, digita los datos en el ERP, compara contra la orden de compra (OC) y la recepción de almacén (*three-way match*), revisa cálculos y cuentas bancarias, y aprueba o devuelve. Es lento (5–10 min por factura), propenso a errores y vulnerable a fraudes como el cambio de cuenta bancaria.

**Métricas objetivo del proyecto (para mostrar en el portafolio):**

| Métrica | Meta |
|---|---|
| Precisión de extracción por campo (evals) | ≥ 95 % |
| Decisión correcta vs. ground truth | ≥ 90 % (15 facturas de prueba) |
| Hallazgos detectados (recall) | 100 % en fraude y duplicados |
| Tiempo por factura | < 20 s de extremo a extremo |
| Costo por factura | < USD 0,02 |

---

## 2. Arquitectura

```
 Outlook ──► Power Automate ──┐
                              ├──► FastAPI  ──► Blob Storage (PDF)
 Web (subir PDF) ─────────────┘       │
                                      ▼
                           LangGraph (pipeline de agentes)
                                      │
      ┌────────────┬──────────────┬───┴─────────┬──────────────┬─────────────┐
      ▼            ▼              ▼             ▼              ▼             ▼
   Ingesta    Extractor      Validador     Conciliador    Riesgo/Fraude   Decisor
   (hash,     (Doc Intel +   (reglas:      (3-way match   (duplicados,    (aprobar /
   tipo)      LLM → schema)  NIT, IVA,     OC + recep-    cuenta nueva,   revisión /
                             totales)      ción)          proveedor)      rechazar +
                                                                          explicación)
                                      │
                                      ▼
                         PostgreSQL (facturas, hallazgos, trazas)
                                      │
                                      ▼
                   Web React: bandeja, detalle, revisión humana, métricas
```

### 2.1 Grafo de agentes (LangGraph)

Estado compartido: `InvoiceState` (ver §3). Cada nodo agrega datos y `findings`; ninguno borra lo de otro.

| # | Nodo | Tipo | Qué hace | Salida |
|---|---|---|---|---|
| 1 | `ingest` | Código | Calcula SHA-256 del archivo, detecta si es PDF nativo o escaneado, guarda en Blob. | `file_hash`, `is_scanned`, `blob_url` |
| 2 | `extract` | Doc Intelligence + código + LLM | `prebuilt-invoice` devuelve campos y confianzas. La normalización de formato (monto colombiano, número de factura `PREFIJO-NUMERO`, fechas ISO, NIT sin DV) es **código determinista** (`app/services/normalize.py`), no LLM — son transformaciones mecánicas, 100 % testeables. El LLM solo interviene para resolver texto libre ambiguo (variaciones de razón social, etiquetas abreviadas del diseño C) al construir `ExtractedInvoice`. | `extracted`, `field_confidence` |
| 3 | `validate` | Reglas | DV del NIT, aritmética de líneas/subtotal/IVA/total, fechas coherentes, CUFE con 96 caracteres hexadecimales. | findings |
| 4 | `match` | Reglas | Busca la OC; compara precio unitario (tolerancia 2 %) y cantidad facturada acumulada vs. cantidad recibida. | findings |
| 5 | `risk` | Reglas + consulta | Proveedor en maestro, factura duplicada (mismo NIT + número o mismo hash), cuenta bancaria distinta a la registrada. | findings |
| 6 | `decide` | Reglas + LLM | La **decisión** sale de la matriz de §4 (determinista). El LLM solo redacta la explicación para el analista y, si aplica, un borrador de correo al proveedor. | `decision`, `explanation`, `supplier_email_draft` |

Aristas condicionales:
- Si `extract` tiene algún campo crítico (NIT, número, total) con confianza < 0,80 → marca `LOW_CONFIDENCE_EXTRACTION` y continúa (no se detiene: el analista verá todo junto).
- Si `risk` detecta `DUPLICATE_INVOICE` → salta directo a `decide` (no tiene sentido conciliar un duplicado).

**Nodo de revisión humana (human-in-the-loop):** las facturas en `REVISION` quedan en la bandeja. El analista aprueba o rechaza desde la web con un comentario; se usa el checkpoint de LangGraph (`interrupt`) para reanudar el grafo y registrar la decisión final.

---

## 3. Esquemas (Pydantic v2)

```python
class InvoiceLine(BaseModel):
    sku: str | None
    description: str
    quantity: Decimal
    unit_price: Decimal
    vat_rate: Decimal          # 0, 5, 19
    line_subtotal: Decimal

class BankAccount(BaseModel):
    bank: str
    account_type: Literal["Ahorros", "Corriente"]
    number: str

class ExtractedInvoice(BaseModel):
    supplier_nit: str          # solo dígitos, sin DV
    supplier_dv: int | None    # DV impreso en la factura
    supplier_name: str
    invoice_number: str        # normalizado "PREFIJO-NUMERO", ej. "LTV-11502"
    issue_date: date
    due_date: date | None
    purchase_order: str | None
    currency: Literal["COP"] = "COP"
    lines: list[InvoiceLine]
    subtotal: Decimal
    vat_total: Decimal
    total: Decimal
    cufe: str | None
    bank_account: BankAccount | None

class Finding(BaseModel):
    code: FindingCode          # enum, ver §4
    severity: Literal["INFO", "MEDIA", "ALTA", "CRITICA"]
    message: str               # en español, legible para el analista
    evidence: dict             # valores comparados, ej. {"oc": 1420000, "factura": 1495000}

class InvoiceState(TypedDict):
    invoice_id: UUID
    file_hash: str
    is_scanned: bool
    extracted: ExtractedInvoice | None
    field_confidence: dict[str, float]
    findings: Annotated[list[Finding], operator.add]
    decision: Literal["APROBAR", "REVISION", "RECHAZAR"] | None
    explanation: str | None
    supplier_email_draft: str | None
```

> Usa `Decimal` para dinero, nunca `float`.

---

## 4. Reglas de negocio

### 4.1 Hallazgos

| Código | Severidad | Regla |
|---|---|---|
| `INVALID_NIT_DV` | ALTA | DV impreso ≠ DV calculado (algoritmo DIAN módulo 11, ver §4.3). |
| `ARITHMETIC_ERROR` | ALTA | Σ líneas ≠ subtotal, Σ IVA por línea ≠ IVA, o subtotal + IVA ≠ total (tolerancia $1). |
| `INVALID_CUFE` | ALTA | `cufe` está presente pero no tiene 96 caracteres hexadecimales válidos. |
| `INCOHERENT_DATES` | MEDIA | `due_date` anterior a `issue_date`, o `issue_date` posterior a la fecha de procesamiento. |
| `UNKNOWN_SUPPLIER` | ALTA | El NIT no está en `proveedores.csv` o el proveedor no está ACTIVO. |
| `MISSING_PO` | MEDIA | La factura no referencia una OC o la OC no existe. |
| `PRICE_MISMATCH` | MEDIA | Precio unitario facturado difiere > 2 % del precio de la OC. |
| `QTY_EXCEEDS_RECEIPT` | MEDIA | Cantidad facturada acumulada (esta + anteriores de la misma OC y SKU) > cantidad recibida. |
| `DUPLICATE_INVOICE` | CRITICA | Mismo NIT + mismo número de factura ya procesado, o mismo hash de archivo. |
| `BANK_ACCOUNT_CHANGED` | CRITICA | La cuenta impresa no coincide con la registrada en el maestro (posible fraude). |
| `LOW_CONFIDENCE_EXTRACTION` | MEDIA | Campo crítico con confianza < 0,80. |
| `AMOUNT_OVER_THRESHOLD` | INFO | Total > $20.000.000: requiere aprobación humana aunque todo cuadre. |

### 4.2 Matriz de decisión

1. `DUPLICATE_INVOICE` o `ARITHMETIC_ERROR` → **RECHAZAR** (se genera borrador de correo pidiendo nota crédito o factura corregida).
2. Cualquier otro hallazgo MEDIA, ALTA o CRITICA, o `AMOUNT_OVER_THRESHOLD` → **REVISION**. `BANK_ACCOUNT_CHANGED` va con prioridad máxima en la bandeja.
3. Sin hallazgos (o solo INFO distinto al umbral) → **APROBAR**.

### 4.3 Dígito de verificación del NIT

Pesos de derecha a izquierda: 3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71. Se multiplica cada dígito por su peso, se suma, se obtiene `r = suma % 11`. Si `r` es 0 o 1, el DV es `r`; si no, `11 − r`.

```python
WEIGHTS = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
def nit_check_digit(nit: str) -> int:
    r = sum(int(d) * WEIGHTS[i] for i, d in enumerate(reversed(nit))) % 11
    return r if r in (0, 1) else 11 - r
```

---

## 5. Modelo de datos (PostgreSQL)

| Tabla | Campos clave |
|---|---|
| `suppliers` | id, nit, dv, name, email, bank, account_type, account_number, status |
| `purchase_orders` | id, number, supplier_id, date, status |
| `po_lines` | id, po_id, sku, description, quantity, unit_price, vat_rate |
| `goods_receipts` | id, po_line_id, quantity_received, received_at |
| `invoices` | id, file_hash, blob_url, status, decision, supplier_id, invoice_number, total, extracted (JSONB), created_at, processed_ms, cost_usd |
| `findings` | id, invoice_id, code, severity, message, evidence (JSONB) |
| `agent_runs` | id, invoice_id, node, started_at, duration_ms, tokens_in, tokens_out, output (JSONB) |
| `reviews` | id, invoice_id, reviewer, action, comment, created_at |

Índice único parcial en `invoices (supplier_id, invoice_number)` excluyendo rechazados por duplicado, y en `file_hash`. Seed desde `data/proveedores.csv`, `ordenes_compra.json` y `recepciones.csv`.

---

## 6. API (FastAPI)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/invoices` | Sube un PDF (multipart). Devuelve `invoice_id` y procesa en segundo plano. |
| GET | `/api/invoices` | Lista con filtros `status`, `decision`, `supplier`, paginada. |
| GET | `/api/invoices/{id}` | Detalle: datos extraídos, confianzas, hallazgos, decisión, explicación. |
| GET | `/api/invoices/{id}/file` | URL firmada (SAS) al PDF. |
| GET | `/api/invoices/{id}/trace` | Pasos del grafo con tiempos, tokens y salida de cada agente. |
| GET | `/api/invoices/{id}/events` | Server-Sent Events con el progreso en vivo del pipeline. |
| POST | `/api/invoices/{id}/review` | `{action: "APROBAR" \| "RECHAZAR", comment}` para reanudar el grafo. |
| GET | `/api/suppliers`, `/api/purchase-orders` | Datos maestros. |
| GET | `/api/metrics` | KPIs para el dashboard. |
| GET | `/api/health` | Health check para Container Apps. |

Autenticación: API key por header para el flujo de Power Automate; login simple (o Microsoft Entra ID si quieres lucir el ecosistema Microsoft) para la web.

---

## 7. Web (React)

Diseño limpio tipo SaaS, modo claro/oscuro, en español.

| Página | Contenido |
|---|---|
| **Landing / Demo** (`/`) | Qué hace, diagrama de arquitectura, botón "Probar con una factura de ejemplo" (usa las 15 de prueba), enlace al repo y a tu LinkedIn. Es la puerta de entrada para reclutadores. |
| **Dashboard** (`/dashboard`) | KPIs: facturas procesadas, % aprobación automática, tiempo promedio, ahorro estimado en horas, costo IA acumulado. Gráfico de decisiones por día y hallazgos más frecuentes. |
| **Bandeja** (`/invoices`) | Tabla con proveedor, número, total, fecha, estado y chips de hallazgos. Filtros y búsqueda. Las de `BANK_ACCOUNT_CHANGED` arriba con alerta roja. |
| **Subir** (`/upload`) | Drag & drop de varios PDFs. Muestra el avance de cada agente en vivo (SSE): Ingesta ✓ → Extracción ✓ → Validación … |
| **Detalle** (`/invoices/:id`) | Vista dividida: PDF a la izquierda; a la derecha campos extraídos con semáforo de confianza, comparación factura vs. OC vs. recepción por línea, hallazgos con evidencia, explicación de la IA y borrador de correo. |
| **Traza** (pestaña del detalle) | Línea de tiempo de los agentes con duración, tokens y costo. Muy útil en entrevistas. |
| **Revisión** (`/review`) | Cola de facturas en REVISION con botones Aprobar/Rechazar y comentario. |
| **Evals** (`/evals`) | Resultado de la última corrida: precisión por campo, matriz de confusión de decisiones, casos fallidos. |

---

## 8. Estructura del repositorio

```
facturia/
├── backend/
│   ├── app/
│   │   ├── api/            # routers FastAPI
│   │   ├── agents/         # nodos: ingest, extract, validate, match, risk, decide
│   │   ├── graph.py        # definición del grafo LangGraph
│   │   ├── rules/          # nit.py, arithmetic.py, matching.py (puro, 100 % testeable)
│   │   ├── schemas/        # Pydantic
│   │   ├── db/             # modelos SQLAlchemy, alembic
│   │   └── services/       # blob, doc_intelligence, llm
│   ├── tests/
│   └── Dockerfile
├── frontend/               # Vite + React + TS
├── evals/
│   ├── run_evals.py        # compara salida vs ground_truth.json
│   └── reports/
├── data/                   # facturas PDF, maestros y ground_truth.json
├── automation/
│   └── power-automate/     # export del flujo + capturas
├── infra/                  # bicep o scripts az cli
├── docker-compose.yml      # api, web, postgres, azurite
├── .github/workflows/      # ci.yml (lint, tests, evals), deploy.yml
└── README.md               # con GIF de demo, arquitectura, métricas, decisiones técnicas
```

---

## 9. Evals

`evals/run_evals.py` procesa las 15 facturas y compara contra `ground_truth.json`:

- **Extracción:** exact match por campo (NIT, número, fechas, OC, totales, cuenta) y por línea (cantidad, precio). Reporta precisión por campo.
- **Hallazgos:** precisión y recall por código.
- **Decisión:** accuracy y matriz de confusión APROBAR / REVISION / RECHAZAR.
- **Operación:** latencia p50/p95 y costo por factura.

Genera `evals/reports/AAAA-MM-DD.md` y la web lo muestra. Corre en CI en cada PR (con un modo `--mock` que usa extracciones cacheadas para no gastar créditos).

**Orden recomendado de procesamiento en evals:** F01 → F15 (F09 solo es duplicado si F01 ya fue procesada).

---

## 10. Plan por fases (≈ 3 semanas a tiempo completo)

| Fase | Entregable | Lo que aprendes |
|---|---|---|
| **1. Base** (días 1–3) | Repo, Docker Compose, FastAPI + Postgres + seed de datos, `rules/` con tests (NIT, aritmética, matching). | FastAPI profesional, SQLAlchemy 2, pytest |
| **2. Extracción** (días 4–6) | Doc Intelligence + normalización LLM con salida estructurada. Primera corrida de evals solo de extracción. | Structured outputs, evals |
| **3. Grafo** (días 7–10) | LangGraph con los 6 nodos, trazas en `agent_runs`, human-in-the-loop. Evals completos. | LangGraph, checkpoints, interrupt |
| **4. Web** (días 11–15) | Bandeja, subir con SSE, detalle con PDF, revisión, dashboard. | React + TanStack Query, SSE |
| **5. RPA + despliegue** (días 16–19) | Flujo Power Automate (Outlook → API), Azure Container Apps + Static Web Apps, GitHub Actions. | Docker, CI/CD, Azure |
| **6. Portafolio** (días 20–21) | README con GIF, diagrama, métricas de evals; video de 2 min; post en LinkedIn. | Comunicar impacto |

---

## 11. Costos y cuentas gratuitas

- **Document Intelligence:** el nivel gratuito F0 incluye un cupo mensual de páginas que alcanza para desarrollo y demo. Verifica los límites actuales en el portal de Azure.
- **Azure OpenAI con modelo mini:** centavos de dólar para cientos de facturas.
- **Container Apps y Static Web Apps:** tienen planes gratuitos o de consumo con cupo mensual.
- Para la demo pública, limita la subida (tamaño máximo 5 MB, rate limit por IP) y ofrece las facturas de ejemplo para no quemar créditos.

---

## 12. Extensiones (si sobra tiempo)

- Leer el **XML UBL 2.1** de la factura electrónica DIAN (AttachedDocument), que trae los datos estructurados y hace la extracción casi exacta; el PDF queda como respaldo.
- Cálculo de **retenciones** (retefuente, reteIVA, reteICA) según tipo de proveedor.
- Chat "pregúntale a tus facturas" con RAG sobre el histórico (conecta con tu Proyecto 1).
- Exportar las aprobadas a un CSV con formato de ERP o a un robot de UiPath que las registre.
