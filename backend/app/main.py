from fastapi import FastAPI

app = FastAPI(title="FacturIA")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
