"""/api/v1 aggregator: mounts resource routers under a version prefix."""

from fastapi import APIRouter

from app.routers import samples

router = APIRouter(prefix="/api/v1")
router.include_router(samples.router)
