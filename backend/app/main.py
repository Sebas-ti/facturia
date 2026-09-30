from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.evals import router as evals_router
from app.api.invoices import router as invoices_router
from app.api.master_data import router as master_data_router
from app.api.metrics import router as metrics_router
from app.config import settings

app = FastAPI(title="FacturIA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(invoices_router)
app.include_router(metrics_router)
app.include_router(evals_router)
app.include_router(master_data_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
