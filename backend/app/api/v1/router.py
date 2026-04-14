"""API v1 main router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()

# Health check (no auth required)
api_router.include_router(health.router, tags=["health"])

# Future routers (uncomment as implemented):
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# api_router.include_router(materials.router, prefix="/materials", tags=["materials"])
# api_router.include_router(channels.router, prefix="/channels", tags=["channels"])
# api_router.include_router(publishing.router, prefix="/publish", tags=["publishing"])
# api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
# api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
