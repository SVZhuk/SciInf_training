"""Application factory (Factory pattern). Run with:

uvicorn app.main:app --reload
open http://127.0.0.1:8000/docs
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import router as api
from app.db import lifespan
from app.frontend import router as frontend

STATIC_DIR = Path(__file__).resolve().parent / "frontend" / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Lab Sample Registry API",
        version="1.0.0",
        description="Teaching demo: REST CRUD over DNA samples.",
        lifespan=lifespan,
    )
    app.include_router(api.router)
    app.include_router(frontend.router)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
