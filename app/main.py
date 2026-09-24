"""Application factory (Factory pattern). Run with:

uvicorn app.main:app --reload
open http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI

from app.routers import samples


def create_app() -> FastAPI:
    app = FastAPI(
        title="Lab Sample Registry API",
        version="1.0.0",
        description="Teaching demo: REST CRUD over DNA samples.",
    )
    app.include_router(samples.router)

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
