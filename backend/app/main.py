"""PhotoCRM API — scaffolding da fundação (apenas /health)."""

from fastapi import FastAPI

app = FastAPI(title="PhotoCRM API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Health check usado pelo Docker Compose e pelo Nginx."""
    return {"status": "ok", "service": "api"}
